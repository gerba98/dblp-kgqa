"""
Selezione della configurazione cross-fitted (two-fold ripetuta, stratificata)
sulle 2.000 domande del test di DBLP-QuAD, senza rilanciare alcun modello.

Uso:
    python splithalf.py --scores scores --repeats 20 --out splithalf_selection.csv

Per ogni ripetizione:
  1. divide le domande in due meta' A/B, stratificate per query_type
     (100 domande per tipo in ciascuna meta');
  2. sceglie su A la configurazione con macro F1 piu' alto e la valuta su B;
  3. fa lo stesso scegliendo su B e valutando su A;
  4. registra le due configurazioni scelte e la media dei due F1 "held-out-half".
Ripete con partizioni casuali diverse (seed 0..repeats-1), per ciascun modello
e per due pool di candidati: tutte le 17 configurazioni, o solo quelle RAG.
"""
import argparse
import glob
import re

import numpy as np
import pandas as pd

GEM = ["Gem_I", "Gem_II", "Gem_III", "Gem_IV", "Gem_V", "Gem_VI", "Gem_VII", "Gem_VIII", "Gem_IX",
       "Gem_VIII_DFS3", "Gem_VIII_DFS10_best", "Gem_VIII_DFS15",
       "Gem_X_DFS10", "Gem_X_DFS10_RRR15", "Gem_X_DFS10_RRR20", "Gem_XI_DFS10_DR", "Gem_XI_DFS10_RRR20_DR"]
QWEN = ["Qwen_I", "Qwen_II", "Qwen_III", "Qwen_IV", "Qwen_V", "Qwen_VI", "Qwen_VII", "Qwen_VIII", "Qwen_IX",
        "Qwen_VIII_DFS3", "Qwen_VIII_DFS10", "Qwen_VIII_DFS15",
        "Qwen_X_DFS15", "Qwen_X_DFS15_RRR15", "Qwen_X_DFS15_RRR20_best", "Qwen_XI_DFS15_DR",
        "Qwen_XI_DFS15_RRR20_DR"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="scores")
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--out", default="splithalf_selection.csv")
    args = ap.parse_args()

    runs = {}
    for f in sorted(glob.glob(f"{args.scores}/*.csv")):
        short = re.sub(r"^\d\d-\d\d-\d\d_\d\d-\d\d-\d\d_test_", "",
                       f.replace("\\", "/").split("/")[-1][:-4])
        runs[short] = pd.read_csv(f).set_index("id")
    ref = runs["Gem_VIII"]

    def halves(seed):
        rng = np.random.default_rng(seed)
        A = []
        for _, g in ref.groupby("query_type"):
            A += list(rng.choice(g.index, size=len(g) // 2, replace=False))
        A = set(A)
        return A, set(ref.index) - A

    def one_split(pool, seed):
        A, B = halves(seed)
        out = []
        for sel, ev in ((list(A), list(B)), (list(B), list(A))):
            best = max(pool, key=lambda c: runs[c].loc[sel, "f1"].mean())
            out.append((best, runs[best].loc[ev, "f1"].mean() * 100))
        return out

    rows = []
    for M, pool in (("Gem", GEM), ("Qwen", QWEN)):
        for label, p in (("all configs", pool), ("RAG only", [c for c in pool if "_X" in c])):
            for seed in range(args.repeats):
                (sa, ob), (sb, oa) = one_split(p, seed)
                rows.append(dict(model=M, pool=label, seed=seed, sel_A=sa, oos_B=ob,
                                 sel_B=sb, oos_A=oa, oos_mean=(ob + oa) / 2))
    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)

    for (M, p), g in df.groupby(["model", "pool"]):
        counts = pd.concat([g.sel_A, g.sel_B]).value_counts().to_dict()
        print(f"{M:5s} {p:12s} held-out-half F1 = {g.oos_mean.mean():.2f} "
              f"(SD {g.oos_mean.std():.2f})  selected: {counts}")
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
