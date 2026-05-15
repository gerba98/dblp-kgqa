from collections.abc import Mapping
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import requests

from dblp_kgqa import PROJECT_ROOT, settings
from dblp_kgqa.experiment.schemas import ExpConfig, ExpResults
from dblp_kgqa.modules.schemas import (
    AskResult,
    SelectResult,
    SparqlResult,
)
from dblp_kgqa.services.dblp_quad import (
    QUERY_TYPE,
    DblpQuadAnswers,
    DblpQuadQuestions,
    DblpQuadService,
    DblpQuadServiceConfig,
)
from dblp_kgqa.utils.yaml import yaml_dump, yaml_load

# %% SPARQL result formatting -------------------------------------------------


def _format_sparql(result: SparqlResult) -> list[str]:
    if isinstance(result.root, AskResult):
        return [str(result.root.boolean).lower()]

    if isinstance(result.root, SelectResult):
        return [
            str(b.value)
            for row in result.root.results.bindings
            for b in row.values()
        ]

    return []


def _format_sparql_target_vars(result: SparqlResult) -> list:
    # Reproduces evaluate_dblp.py get_answer(): priority chain
    # ?answer > (?firstanswer, ?secondanswer) > ?count.
    if isinstance(result.root, AskResult):
        return [str(result.root.boolean).lower()]

    if isinstance(result.root, SelectResult):
        head_vars = set(result.root.head.vars)
        bindings = result.root.results.bindings

        if {"firstanswer", "secondanswer"} <= head_vars:
            return [
                (
                    str(row["firstanswer"].value)
                    if "firstanswer" in row
                    else None,
                    str(row["secondanswer"].value)
                    if "secondanswer" in row
                    else None,
                )
                for row in bindings
            ]

        if "answer" in head_vars:
            target = "answer"
        elif "count" in head_vars:
            target = "count"
        else:
            return []

        return [str(row[target].value) for row in bindings if target in row]

    return []


# %% Data preparation ---------------------------------------------------------


def _build_gold_data(
    questions: DblpQuadQuestions,
    answers: DblpQuadAnswers,
) -> tuple[
    dict[str, list[str]],
    dict[str, list],
    dict[str, list[str]],
    dict[str, QUERY_TYPE],
]:
    qa_all: dict[str, list[str]] = {}
    qa_target: dict[str, list] = {}
    entities: dict[str, list[str]] = {}
    qt_map: dict[str, QUERY_TYPE] = {}

    for q, a in zip(questions.questions, answers.answers, strict=True):
        qa_all[q.id] = _format_sparql(a.answer)
        qa_target[q.id] = _format_sparql_target_vars(a.answer)
        entities[q.id] = q.entities
        qt_map[q.id] = q.query_type

    return qa_all, qa_target, entities, qt_map


def _build_system_data(
    exp_results: ExpResults,
) -> tuple[
    dict[str, list[str]],
    dict[str, list],
    dict[str, list[str]],
]:
    qa_all: dict[str, list[str]] = {}
    qa_target: dict[str, list] = {}
    entities: dict[str, list[str]] = {}

    for r in exp_results.exp_results:
        if r.result.sparql_result:
            res = r.result.sparql_result
            qa_all[r.id] = _format_sparql(res)
            qa_target[r.id] = _format_sparql_target_vars(res)
        else:
            qa_all[r.id] = []
            qa_target[r.id] = []

        entities[r.id] = [
            e.uri if e.uri else e.name
            for e in r.result.linked_entities.linked_entities
        ]

    return qa_all, qa_target, entities


# %% Per-query metrics --------------------------------------------------------


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * p * r) / (p + r) if (p + r) else 0.0
    return p, r, f1


def compute_per_query(
    gold: dict[str, list[str]],
    system: dict[str, list[str]],
    qt_map: Mapping[str, str],
) -> pd.DataFrame:
    rows = []
    for qid, gold_vals in gold.items():
        sys_vals = system.get(qid, [])
        gs, ss = set(gold_vals), set(sys_vals)

        tp = len(gs & ss)
        fp = len(ss - gs)
        fn = len(gs - ss)
        p, r, f1 = _prf(tp, fp, fn)

        rows.append(
            {
                "id": qid,
                "query_type": qt_map.get(qid, "UNKNOWN"),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": p,
                "recall": r,
                "f1": f1,
                "exact_match": fp == 0 and fn == 0,
                "empty": len(sys_vals) == 0,
            }
        )

    return pd.DataFrame(rows)


# %% DBLP-QuAD macro ----------------------------------------------------------
# Reproduces evaluate_dblp.py calculate_f1(): empty gold or system answers are
# skipped from P/R accumulation but still counted in the denominator (implicit
# P=0, R=0). P/R use len(list), not len(set). F1 is derived from averaged P/R,
# not from per-query F1s.


def _dblp_quad_macro_for_group(
    gold: dict[str, list],
    system: dict[str, list],
    qids: list[str],
) -> tuple[float, float, float, int]:
    precisions: list[float] = []
    recalls: list[float] = []
    total = len(qids)

    for qid in qids:
        gv = gold.get(qid, [])
        sv = system.get(qid, [])

        if not gv or not sv:
            continue

        tp = len(set(gv) & set(sv))
        precisions.append(tp / len(sv))
        recalls.append(tp / len(gv))

    if not total:
        return 0.0, 0.0, 0.0, 0

    macro_p = float(np.sum(precisions) / total)
    macro_r = float(np.sum(recalls) / total)
    denom = macro_p + macro_r
    f1 = (2 * macro_p * macro_r) / denom if denom else 0.0

    return macro_p, macro_r, f1, len(precisions)


# %% Aggregation --------------------------------------------------------------


def _aggregate_group(
    df: pd.DataFrame,
    gold_target: dict[str, list],
    sys_target: dict[str, list],
) -> dict:
    n = len(df)
    if n == 0:
        return {
            "n": 0,
            "micro_p": 0.0,
            "micro_r": 0.0,
            "micro_f1": 0.0,
            "macro_p": 0.0,
            "macro_r": 0.0,
            "macro_f1": 0.0,
            "dblp_p": 0.0,
            "dblp_r": 0.0,
            "dblp_f1": 0.0,
            "em": 0.0,
            "empty": 0,
        }

    total_tp = int(df["tp"].sum())
    total_fp = int(df["fp"].sum())
    total_fn = int(df["fn"].sum())
    micro_p, micro_r, micro_f1 = _prf(total_tp, total_fp, total_fn)

    macro_p = float(df["precision"].mean())
    macro_r = float(df["recall"].mean())
    macro_f1 = float(df["f1"].mean())

    qids = df["id"].tolist()
    dblp_p, dblp_r, dblp_f1, _ = _dblp_quad_macro_for_group(
        gold_target, sys_target, qids
    )

    em = float(df["exact_match"].mean())
    empty = int(df["empty"].sum())

    return {
        "n": n,
        "micro_p": micro_p,
        "micro_r": micro_r,
        "micro_f1": micro_f1,
        "macro_p": macro_p,
        "macro_r": macro_r,
        "macro_f1": macro_f1,
        "dblp_p": dblp_p,
        "dblp_r": dblp_r,
        "dblp_f1": dblp_f1,
        "em": em,
        "empty": empty,
    }


def build_summary(
    per_query_df: pd.DataFrame,
    gold_target: dict[str, list],
    sys_target: dict[str, list],
) -> pd.DataFrame:
    rows = []

    for qt in sorted(per_query_df["query_type"].unique()):
        group = per_query_df[per_query_df["query_type"] == qt]
        row = _aggregate_group(group, gold_target, sys_target)
        row["query_type"] = qt
        rows.append(row)

    total_row = _aggregate_group(per_query_df, gold_target, sys_target)
    total_row["query_type"] = "TOTAL"
    rows.append(total_row)

    df = pd.DataFrame(rows)
    cols = [
        "query_type",
        "n",
        "micro_p",
        "micro_r",
        "micro_f1",
        "macro_p",
        "macro_r",
        "macro_f1",
        "dblp_p",
        "dblp_r",
        "dblp_f1",
        "em",
        "empty",
    ]
    return df[cols]


# %% Main entry point ---------------------------------------------------------

TaskType = Literal["qa", "el", "both"]


def evaluate(
    exp_results: ExpResults,
    dataset_questions: DblpQuadQuestions,
    dataset_answers: DblpQuadAnswers,
    tasks: TaskType = "both",
) -> dict[str, pd.DataFrame]:
    gold_qa_all, gold_qa_target, gold_el, qt_map = _build_gold_data(
        dataset_questions, dataset_answers
    )
    sys_qa_all, sys_qa_target, sys_el = _build_system_data(exp_results)

    results: dict[str, pd.DataFrame] = {}

    if tasks in ("qa", "both"):
        pq = compute_per_query(gold_qa_all, sys_qa_all, qt_map)
        results["qa"] = build_summary(pq, gold_qa_target, sys_qa_target)

    if tasks in ("el", "both"):
        pq = compute_per_query(gold_el, sys_el, qt_map)
        results["el"] = build_summary(pq, gold_el, sys_el)

    return results


# %% Export helpers -----------------------------------------------------------


def format_summary(df: pd.DataFrame, decimals: int = 3) -> pd.DataFrame:
    out = df.copy()
    float_cols = [
        c for c in out.columns if out[c].dtype == float and c != "em"
    ]
    out[float_cols] = out[float_cols].round(decimals)
    em_pct = (out["em"] * 100).round(1).astype(str)
    out["em"] = em_pct + "%"
    out["empty"] = out["empty"].astype(int)
    return out


def save_metrics(
    results: dict[str, pd.DataFrame],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for task, df in results.items():
        df.to_csv(output_dir / f"{task}_metrics.csv", index=False)


def print_metrics(results: dict[str, pd.DataFrame]) -> None:
    for task, df in results.items():
        print(f"\n{'=' * 125}")
        print(f"  {task.upper()} METRICS")
        print(f"{'=' * 125}")
        print(format_summary(df).to_string(index=False))
        print()


def to_latex(
    results: dict[str, pd.DataFrame], decimals: int = 3
) -> dict[str, str]:
    latex: dict[str, str] = {}
    for task, df in results.items():
        formatted = format_summary(df, decimals)
        latex[task] = formatted.to_latex(index=False)
    return latex


# %% Discord notification -----------------------------------------------------


def send_metrics_to_discord(
    results: dict[str, pd.DataFrame],
    exp_config: ExpConfig | None = None,
) -> None:
    if settings.discord_webhook_url is None:
        print("DISCORD_WEBHOOK_URL not set, skipping")
        return
    webhook_url = settings.discord_webhook_url.get_secret_value()

    lines = []
    if exp_config is not None:
        lines.append(f"**Split**: `{exp_config.split}`")
        lines.append(f"**Description**: {exp_config.exp_description}")

    for task, df in results.items():
        total = df[df["query_type"] == "TOTAL"].iloc[0]
        lines.append(f"\n**{task.upper()} Results**")
        lines.append(f"Exact Match: **{total['em'] * 100:.1f}%**")
        lines.append(f"Micro F1: **{total['micro_f1']:.4f}**")
        lines.append(f"DBLP Macro F1: **{total['dblp_f1']:.4f}**")
        lines.append(f"Samples: {int(total['n'])}")
        lines.append(f"Empty: {int(total['empty'])}")

    embed = {
        "title": "EXPERIMENT COMPLETED",
        "description": "\n".join(lines),
        "color": 0x57F287,
    }
    bot = {"username": "masters-thesis results"}

    resp = requests.post(
        webhook_url,
        json={**bot, "embeds": [embed]},
    )
    if resp.status_code not in (200, 204):
        print(f"Discord failed: {resp.status_code} {resp.text}")
        return

    import json as _json

    files: dict[str, tuple[str, str, str]] = {}
    for task, df in results.items():
        table = format_summary(df).to_string(index=False)
        files[f"file_{task}"] = (
            f"{task}_metrics.txt", table, "text/plain"
        )
    if exp_config is not None:
        files["file_config"] = (
            "exp_config.yaml",
            yaml_dump(exp_config),
            "text/plain",
        )

    resp = requests.post(
        webhook_url,
        data={"payload_json": _json.dumps(bot)},
        files=files,
    )
    if resp.status_code in (200, 204):
        print("Metrics sent to Discord.")
    else:
        print(f"Discord failed: {resp.status_code} {resp.text}")


# %% Standalone execution -----------------------------------------------------

if __name__ == "__main__":
    curr_exp_dir_name = "26-04-27_11-13-12_test_Gem_VIII"

    exp_dir = (
        PROJECT_ROOT / "experiment_output" / "results" / curr_exp_dir_name
    )
    exp_results = ExpResults.model_validate_json(
        (exp_dir / "exp_results.json").read_text(encoding="utf-8")
    )
    exp_config = yaml_load(ExpConfig, exp_dir / "exp_config.yml")

    dblp_quad_service = DblpQuadService(DblpQuadServiceConfig())
    dataset_questions = dblp_quad_service.load("test", "questions")
    dataset_answers = dblp_quad_service.load("test", "answers")

    results = evaluate(
        exp_results, dataset_questions, dataset_answers, tasks="qa"
    )

    save_metrics(results, exp_dir)
    print_metrics(results)
    send_metrics_to_discord(results, exp_config)
