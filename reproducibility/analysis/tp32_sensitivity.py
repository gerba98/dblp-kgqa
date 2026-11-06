"""Sensitivity analysis for the gold-answer defect of DBLP-QuAD template TP32.

The 25 test questions of template TP32 are BOOLEAN questions whose gold
queries use dcterms:bibtexType, a predicate that does not occur in the DBLP
knowledge graph, instead of dblp:bibtexType. Their official gold answers are
therefore always False, while the correct answer is True for all 25.

This script rewrites the per-question score files produced by
extract_scores.py in one of two ways:

  --mode exclude   drop the 25 TP32 questions (1,975 questions remain)
  --mode correct   score the 25 TP32 questions against the corrected gold
                   answer True: F1 = EM = 1 if the system returned the
                   boolean True, 0 otherwise (requires exp_results.json)

The output directory can then be passed to analyze_all.py and splithalf.py
unchanged, e.g.:

    python tp32_sensitivity.py --mode correct --scores scores \
        --runs runs_root --questions gold/questions.json --out scores_tp32_corrected
    python analyze_all.py --scores scores_tp32_corrected --out stats_tp32_corrected.xlsx
"""

import argparse
import csv
import glob
import json
import os

csv.field_size_limit(10**9)


def tp32_ids(questions_path):
    with open(questions_path, encoding="utf-8") as f:
        questions = json.load(f)["questions"]
    return {q["id"] for q in questions if q.get("template_id") == "TP32"}


def system_booleans(results_path):
    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)
    items = list(data.values())[0] if isinstance(data, dict) else data
    out = {}
    for it in items:
        sr = ((it.get("result") or {}).get("sparql_result")) or {}
        out[it["id"]] = isinstance(sr, dict) and sr.get("boolean") is True
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["exclude", "correct"], required=True)
    ap.add_argument("--scores", required=True, help="directory with the per-question CSV files")
    ap.add_argument("--questions", required=True, help="DBLP-QuAD test questions.json")
    ap.add_argument("--runs", help="directory with one sub-directory per run containing exp_results.json (mode correct)")
    ap.add_argument("--out", required=True, help="output directory")
    args = ap.parse_args()
    if args.mode == "correct" and not args.runs:
        ap.error("--runs is required with --mode correct")

    tp = tp32_ids(args.questions)
    os.makedirs(args.out, exist_ok=True)
    changed = 0
    for path in sorted(glob.glob(os.path.join(args.scores, "*.csv"))):
        run = os.path.basename(path)[:-4]
        answers = system_booleans(os.path.join(args.runs, run, "exp_results.json")) if args.mode == "correct" else None
        with open(path, encoding="utf-8", newline="") as fi, \
                open(os.path.join(args.out, run + ".csv"), "w", encoding="utf-8", newline="") as fo:
            reader = csv.DictReader(fi)
            writer = csv.DictWriter(fo, fieldnames=reader.fieldnames)
            writer.writeheader()
            for row in reader:
                if row["id"] in tp:
                    if args.mode == "exclude":
                        continue
                    ok = answers.get(row["id"], False)
                    new = "1.0" if ok else "0.0"
                    if float(row["f1"]) != float(new):
                        changed += 1
                    row["f1"] = new
                    row["em"] = "1" if ok else "0"
                writer.writerow(row)
    print(f"TP32 questions: {len(tp)}; mode: {args.mode}; scores changed: {changed}")


if __name__ == "__main__":
    main()
