"""
Test statistici appaiati fra due run del pipeline dblp-kgqa.

Uso:
    python stat_tests.py <run_A>/exp_results.json <run_B>/exp_results.json \
        --data data/dblp_quad/test [--margin 1.0] [--n-boot 10000]

Confronta A contro B (differenza = A - B) sulle stesse 2000 domande del test:
  - macro F1: bootstrap appaiato (IC 95%), p-value bootstrap, Wilcoxon
  - exact match: test di McNemar
  - non-inferiorita' di A rispetto a B con margine prefissato (in punti F1)
  - breakdown per query type
Salva anche per_question_<A>_vs_<B>.csv con i punteggi per domanda.

Dipendenze: numpy, pandas, scipy, statsmodels
La logica di flattening delle risposte replica esattamente evaluate.py del repo.
"""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from statsmodels.stats.contingency_tables import mcnemar


# --- caricamento -------------------------------------------------------------

def _fix_unicode(text: str) -> str:
    return re.sub(r"\\\\u([0-9a-fA-F]{4})",
                  lambda m: chr(int(m.group(1), 16)), text)


def load_json(path: Path):
    return json.loads(_fix_unicode(path.read_text(encoding="utf-8")))


def flatten(result) -> list[str]:
    """Replica _format_sparql di evaluate.py."""
    if result is None:
        return []
    if "boolean" in result:
        return [str(result["boolean"]).lower()]
    if "results" in result:
        return [str(b["value"])
                for row in result["results"]["bindings"]
                for b in row.values()]
    return []


def per_question(gold: dict, system: dict, meta: dict) -> pd.DataFrame:
    rows = []
    for qid, g in gold.items():
        s = system.get(qid, [])
        gs, ss = set(g), set(s)
        tp, fp, fn = len(gs & ss), len(ss - gs), len(gs - ss)
        p = tp / (tp + fp) if tp + fp else 0.0
        r = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * p * r / (p + r) if p + r else 0.0
        rows.append({"id": qid, **meta[qid], "f1": f1,
                     "em": int(fp == 0 and fn == 0), "empty": int(not s)})
    return pd.DataFrame(rows)


# --- test --------------------------------------------------------------------

def paired_bootstrap(diff: np.ndarray, n_boot: int, seed: int = 0):
    rng = np.random.default_rng(seed)
    n = len(diff)
    idx = rng.integers(0, n, size=(n_boot, n))
    means = diff[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    obs = diff.mean()
    # p-value bootstrap a due code (H0: media = 0), con shift
    centered = means - obs
    p = 2 * min((centered >= obs).mean(), (centered <= obs).mean())
    return obs, lo, hi, min(p, 1.0)


def mcnemar_em(em_a: np.ndarray, em_b: np.ndarray):
    b = int(((em_a == 1) & (em_b == 0)).sum())   # A giusta, B sbagliata
    c = int(((em_a == 0) & (em_b == 1)).sum())   # A sbagliata, B giusta
    res = mcnemar([[0, b], [c, 0]], exact=(b + c) < 25)
    return b, c, float(res.pvalue)


def report(df_a: pd.DataFrame, df_b: pd.DataFrame, label: str,
           margin: float, n_boot: int) -> dict:
    m = df_a.merge(df_b, on="id", suffixes=("_a", "_b"))
    diff = (m["f1_a"] - m["f1_b"]).to_numpy() * 100  # in punti percentuali
    obs, lo, hi, p_boot = paired_bootstrap(diff, n_boot)
    try:
        p_wil = float(wilcoxon(m["f1_a"], m["f1_b"]).pvalue)
    except ValueError:  # tutte le differenze sono zero
        p_wil = 1.0
    b, c, p_mc = mcnemar_em(m["em_a"].to_numpy(), m["em_b"].to_numpy())
    return {
        "group": label, "n": len(m),
        "macroF1_A": m["f1_a"].mean() * 100, "macroF1_B": m["f1_b"].mean() * 100,
        "diff_pp": obs, "ci95_lo": lo, "ci95_hi": hi,
        "p_bootstrap": p_boot, "p_wilcoxon": p_wil,
        "EM_A": m["em_a"].mean() * 100, "EM_B": m["em_b"].mean() * 100,
        "mcnemar_b": b, "mcnemar_c": c, "p_mcnemar": p_mc,
        "significant_05": bool(lo > 0 or hi < 0),
        # A non-inferiore a B: A non perde piu' di `margin` punti rispetto a B
        f"A_noninf_to_B_m{margin}": bool(lo > -margin),
        # B non-inferiore ad A: B non perde piu' di `margin` punti rispetto ad A
        f"B_noninf_to_A_m{margin}": bool(hi < margin),
    }


# --- main --------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_a")
    ap.add_argument("run_b")
    ap.add_argument("--data", default="data/dblp_quad/test",
                    help="cartella con questions.json e answers.json")
    ap.add_argument("--margin", type=float, default=1.0,
                    help="margine di non-inferiorita' in punti F1")
    ap.add_argument("--n-boot", type=int, default=10000)
    args = ap.parse_args()

    data = Path(args.data)
    questions = load_json(data / "questions.json")["questions"]
    answers = load_json(data / "answers.json")["answers"]
    meta = {q["id"]: {"query_type": q["query_type"],
                      "template_id": q["template_id"],
                      "held_out": q["held_out"]} for q in questions}
    gold = {a["id"]: flatten(a["answer"]) for a in answers}

    def load_run(p):
        res = load_json(Path(p))["exp_results"]
        return {r["id"]: flatten(r["result"].get("sparql_result"))
                for r in res}

    df_a = per_question(gold, load_run(args.run_a), meta)
    df_b = per_question(gold, load_run(args.run_b), meta)

    name_a = Path(args.run_a).parent.name or "A"
    name_b = Path(args.run_b).parent.name or "B"

    rows = [report(df_a, df_b, "TOTAL", args.margin, args.n_boot)]
    for qt in sorted(df_a["query_type"].unique()):
        rows.append(report(df_a[df_a.query_type == qt],
                           df_b[df_b.query_type == qt], qt,
                           args.margin, args.n_boot))
    for ho in (False, True):
        rows.append(report(df_a[df_a.held_out == ho],
                           df_b[df_b.held_out == ho],
                           f"held_out={ho}", args.margin, args.n_boot))

    out = pd.DataFrame(rows)
    pd.set_option("display.width", 250)
    print(f"\nA = {name_a}\nB = {name_b}\n(diff = A - B, punti percentuali)\n")
    print(out.round(3).to_string(index=False))

    merged = df_a.merge(df_b, on="id", suffixes=(f"_{name_a}", f"_{name_b}"))
    csv = f"per_question_{name_a}_vs_{name_b}.csv"
    merged.to_csv(csv, index=False)
    out.to_csv(f"stats_{name_a}_vs_{name_b}.csv", index=False)
    print(f"\nSalvati: {csv}, stats_{name_a}_vs_{name_b}.csv")


if __name__ == "__main__":
    main()
