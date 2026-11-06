"""
Estrae i punteggi per domanda da tutte le cartelle di run e li salva in scores/.

Uso (dalla cartella stat_tests, con venv attivo):
    python extract_scores.py --data gold

Per ogni cartella che contiene exp_results.json produce scores/<nome_cartella>.csv
con: id, query_type, template_id, held_out, f1, em, empty, n_gold, n_sys,
e (per i run RAG) i predicati recuperati, per calcolare il Recall@m.
Copia anche exp_config.yml come scores/<nome_cartella>.config.yml.
Alla fine crea scores.zip, pronto da caricare.
"""

import argparse
import json
import re
import shutil
from pathlib import Path

import pandas as pd


def _fix_unicode(text):
    return re.sub(r"\\\\u([0-9a-fA-F]{4})",
                  lambda m: chr(int(m.group(1), 16)), text)


def load_json(path):
    return json.loads(_fix_unicode(Path(path).read_text(encoding="utf-8")))


def flatten(result):
    if result is None:
        return []
    if "boolean" in result:
        return [str(result["boolean"]).lower()]
    if "results" in result:
        return [str(b["value"]) for row in result["results"]["bindings"]
                for b in row.values()]
    return []


def retrieved_predicates(r):
    """Prova a recuperare i predicati selezionati dal Relation Linker."""
    lr = r.get("result", {}).get("linked_relation") or {}
    ctx = lr.get("schema_context") or lr.get("predicates") or lr.get("relations")
    if not ctx:
        return ""
    names = []
    for p in ctx:
        if isinstance(p, dict):
            names.append(str(p.get("uri") or p.get("id") or p.get("name") or p))
        else:
            names.append(str(p))
    return "|".join(names)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="gold")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    data = Path(args.data)
    questions = load_json(data / "questions.json")["questions"]
    answers = load_json(data / "answers.json")["answers"]
    meta = {q["id"]: {"query_type": q["query_type"],
                      "template_id": q["template_id"],
                      "held_out": q["held_out"],
                      "gold_relations": "|".join(q.get("relations", []))}
            for q in questions}
    gold = {a["id"]: flatten(a["answer"]) for a in answers}

    out = Path("scores")
    out.mkdir(exist_ok=True)
    n_runs = 0
    for res_file in sorted(Path(args.root).glob("*/exp_results.json")):
        run = res_file.parent.name
        results = load_json(res_file)["exp_results"]
        sysmap = {r["id"]: r for r in results}
        rows = []
        for qid, g in gold.items():
            r = sysmap.get(qid)
            s = flatten(r["result"].get("sparql_result")) if r else []
            gs, ss = set(g), set(s)
            tp, fp, fn = len(gs & ss), len(ss - gs), len(gs - ss)
            p = tp / (tp + fp) if tp + fp else 0.0
            rc = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * p * rc / (p + rc) if p + rc else 0.0
            rows.append({"id": qid, **meta[qid], "f1": f1,
                         "em": int(fp == 0 and fn == 0), "empty": int(not s),
                         "n_gold": len(gs), "n_sys": len(ss),
                         "retrieved": retrieved_predicates(r) if r else ""})
        df = pd.DataFrame(rows)
        df.to_csv(out / f"{run}.csv", index=False)
        cfg = res_file.parent / "exp_config.yml"
        if cfg.exists():
            shutil.copy(cfg, out / f"{run}.config.yml")
        n_runs += 1
        print(f"{run}: macro F1 = {df.f1.mean():.4f}, EM = {df.em.mean():.4f}")

    shutil.make_archive("scores", "zip", out)
    print(f"\n{n_runs} run estratti. Carica il file scores.zip.")


if __name__ == "__main__":
    main()
