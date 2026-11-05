"""
Analisi statistica completa dei run DBLP-QuAD a partire dai CSV per domanda
prodotti da extract_scores.py (cartella scores/).

Uso:
    python analyze_all.py --scores scores --out statistical_analysis.xlsx

Produce un Excel con i fogli:
  totals                  confronti appaiati sul test completo (2.000 domande)
  all_breakdowns          gli stessi confronti per query type e seen/held-out
  seen_vs_heldout         macro F1 di ogni run su template visti / non visti
  retriever_recall        copertura e Recall@m del Relation Linker, F1 hit/miss
  predicate_coverage_m20  % di recupero di ciascun predicato gold a m=20

Dipendenze: numpy, pandas, scipy, statsmodels, openpyxl
"""
import argparse
import glob
import json
import re

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon
from statsmodels.stats.contingency_tables import mcnemar

N_BOOT = 10000


def load_runs(scores_dir):
    runs = {}
    for f in sorted(glob.glob(f"{scores_dir}/*.csv")):
        name = f.replace("\\", "/").split("/")[-1][:-4]
        short = re.sub(r"^\d\d-\d\d-\d\d_\d\d-\d\d-\d\d_test_", "", name)
        runs[short] = pd.read_csv(f)
    return runs


def boot(diff, n=N_BOOT, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff), size=(n, len(diff)))
    means = diff[idx].mean(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    obs = diff.mean()
    c = means - obs
    p = 2 * min((c >= obs).mean(), (c <= obs).mean())
    return obs, lo, hi, min(p, 1.0)


def cmp(runs, a, b, label, sub=None):
    m = runs[a].merge(runs[b], on="id", suffixes=("_a", "_b"))
    if sub is not None:
        m = m[sub(m)]
    diff = (m.f1_a - m.f1_b).to_numpy() * 100
    obs, lo, hi, pb = boot(diff)
    try:
        pw = wilcoxon(m.f1_a, m.f1_b).pvalue
    except ValueError:
        pw = 1.0
    bb = int(((m.em_a == 1) & (m.em_b == 0)).sum())
    cc = int(((m.em_a == 0) & (m.em_b == 1)).sum())
    pm = mcnemar([[0, bb], [cc, 0]], exact=(bb + cc) < 25).pvalue
    return dict(comparison=label, A=a, B=b, n=len(m),
                F1_A=round(m.f1_a.mean() * 100, 2), F1_B=round(m.f1_b.mean() * 100, 2),
                diff=round(obs, 2), ci_lo=round(lo, 2), ci_hi=round(hi, 2),
                p_boot=round(pb, 4), p_wilcoxon=round(pw, 4),
                EM_A=round(m.em_a.mean() * 100, 2), EM_B=round(m.em_b.mean() * 100, 2),
                mc_b=bb, mc_c=cc, p_mcnemar=round(pm, 4),
                significant=bool(lo > 0 or hi < 0),
                B_noninf_1pt=bool(hi < 1.0), A_noninf_1pt=bool(lo > -1.0))


def full(runs, a, b, label):
    rows = [cmp(runs, a, b, label)]
    for qt in sorted(runs[a].query_type.unique()):
        r = cmp(runs, a, b, label, lambda m, qt=qt: m.query_type_a == qt)
        r["comparison"] = f"{label} | {qt}"
        rows.append(r)
    for ho in (False, True):
        r = cmp(runs, a, b, label, lambda m, ho=ho: m.held_out_a == ho)
        r["comparison"] = f"{label} | held_out={ho}"
        rows.append(r)
    return rows


def pairs_for(M):
    P = [(f"{M}_V", f"{M}_III", "T7 dynamic vs static (DFS vs SFS)"),
         (f"{M}_III", f"{M}_I", "T7 SFS vs SP"),
         (f"{M}_II", f"{M}_I", "T7 CoT vs SP"),
         (f"{M}_IV", f"{M}_III", "T7 SFS+CoT vs SFS"),
         (f"{M}_VI", f"{M}_V", "T7 FQT on DFS"),
         (f"{M}_VII", f"{M}_V", "T7 CoT on DFS"),
         (f"{M}_VIII", f"{M}_VI", "T7 CoT on DFS+FQT"),
         (f"{M}_VIII", f"{M}_V", "T7 FQT+CoT on DFS"),
         (f"{M}_IX", f"{M}_VIII", "T7 SFS added to full dynamic"),
         (f"{M}_VIII", f"{M}_VIII_DFS3", "T8 k=5 vs k=3")]
    k10 = f"{M}_VIII_DFS10" + ("_best" if M == "Gem" else "")
    P += [(k10, f"{M}_VIII", "T8 k=10 vs k=5"),
          (f"{M}_VIII_DFS15", k10, "T8 k=15 vs k=10")]
    fs = k10 if M == "Gem" else f"{M}_VIII_DFS15"
    kk = "DFS10" if M == "Gem" else "DFS15"
    rag10 = f"{M}_X_{kk}"
    rag15 = f"{M}_X_{kk}_RRR15"
    rag20 = f"{M}_X_{kk}_RRR20" + ("_best" if M == "Qwen" else "")
    dr10 = f"{M}_XI_{kk}_DR"
    dr20 = f"{M}_XI_{kk}_RRR20_DR"
    P += [(fs, rag10, "T9 FS vs RAG m=10"), (fs, rag15, "T9 FS vs RAG m=15"),
          (fs, rag20, "T9 FS vs RAG m=20"), (fs, dr10, "T9 FS vs RAG+DR m=10"),
          (fs, dr20, "T9 FS vs RAG+DR m=20"), (rag20, rag10, "T9 RAG m=20 vs m=10"),
          (dr10, rag10, "T9 DR effect m=10"), (dr20, rag20, "T9 DR effect m=20")]
    return P


def norm(iri):
    return iri.strip("<>").split("#")[-1].split("/")[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="scores")
    ap.add_argument("--out", default="statistical_analysis.xlsx")
    args = ap.parse_args()
    runs = load_runs(args.scores)

    pairs = pairs_for("Gem") + pairs_for("Qwen")
    pairs += [("Gem_VIII_DFS15", "Qwen_VIII_DFS15", "T10 Cloud vs Local (k=15, FS)"),
              ("Qwen25Coder_X_DFS15_RRR20_ask-dblp", "Qwen_X_DFS15_RRR20_best",
               "Extra Qwen2.5-Coder-32B vs Qwen3.5-4B (RAG m=20)"),
              ("Gem_VIII_DFS10_best", "Qwen25Coder_X_DFS15_RRR20_ask-dblp",
               "Extra Gemini FS vs Qwen2.5-Coder-32B RAG")]
    rows = []
    for a, b, lab in pairs:
        if a in runs and b in runs:
            rows += full(runs, a, b, lab)
        else:
            print("MISSING", a, b)
    stats = pd.DataFrame(rows)

    seen = pd.DataFrame([dict(
        run=name, macroF1=d.f1.mean() * 100, EM=d.em.mean() * 100, empty=int(d["empty"].sum()),
        F1_seen=d[~d.held_out].f1.mean() * 100, F1_heldout=d[d.held_out].f1.mean() * 100,
        n_seen=int((~d.held_out).sum()), n_heldout=int(d.held_out.sum()))
        for name, d in runs.items()]).round(2)

    rr = []
    for name, d in runs.items():
        if "_X_" not in name and "_XI_" not in name:
            continue
        cov, ok_all, miss_f1, hit_f1 = [], [], [], []
        for _, r in d.iterrows():
            if not isinstance(r.retrieved, str) or not isinstance(r.gold_relations, str):
                continue
            ret = {norm(v["IRI"]) for v in json.loads(r.retrieved).values()}
            gold = {norm(p) for p in r.gold_relations.split("|") if p}
            if not gold:
                continue
            cov.append(len(gold & ret) / len(gold))
            ok = gold <= ret
            ok_all.append(ok)
            (hit_f1 if ok else miss_f1).append(r.f1)
        rr.append(dict(run=name, n=len(cov), pred_coverage=np.mean(cov) * 100,
                       recall_all_gold=np.mean(ok_all) * 100, n_miss=len(miss_f1),
                       F1_when_all_gold_retrieved=np.mean(hit_f1) * 100,
                       F1_when_some_gold_missing=np.mean(miss_f1) * 100 if miss_f1 else np.nan))
    retr = pd.DataFrame(rr).round(2)

    pc = {}
    for _, r in runs["Gem_X_DFS10_RRR20"].iterrows():
        if not isinstance(r.retrieved, str) or not isinstance(r.gold_relations, str):
            continue
        ret = {norm(v["IRI"]) for v in json.loads(r.retrieved).values()}
        for p in {norm(p) for p in r.gold_relations.split("|") if p}:
            pc.setdefault(p, [0, 0])
            pc[p][0] += 1
            pc[p][1] += int(p in ret)
    predcov = pd.DataFrame([dict(predicate=p, n_questions=v[0], retrieved_pct=round(v[1] / v[0] * 100, 1))
                            for p, v in pc.items()]).sort_values("n_questions", ascending=False)

    with pd.ExcelWriter(args.out) as w:
        stats[~stats.comparison.str.contains(r"\|")].to_excel(w, sheet_name="totals", index=False)
        stats.to_excel(w, sheet_name="all_breakdowns", index=False)
        seen.to_excel(w, sheet_name="seen_vs_heldout", index=False)
        retr.to_excel(w, sheet_name="retriever_recall", index=False)
        predcov.to_excel(w, sheet_name="predicate_coverage_m20", index=False)
    print(f"Saved {args.out}: {len(stats)} comparison rows, {len(runs)} runs")


if __name__ == "__main__":
    main()
