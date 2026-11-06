"""
Verifica indipendente dei test statistici usando solo funzioni di libreria
(scipy.stats.bootstrap, scipy.stats.wilcoxon, statsmodels mcnemar).

Uso (nella cartella con scores/ estratta da scores.zip):
    python verify.py scores/<runA>.csv scores/<runB>.csv

Stampa differenza macro F1 (A - B, punti), IC 95% bootstrap appaiato,
p di Wilcoxon, conteggi e p di McNemar. Da confrontare con l'Excel.
"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import bootstrap, wilcoxon
from statsmodels.stats.contingency_tables import mcnemar

a = pd.read_csv(sys.argv[1]).set_index("id")
b = pd.read_csv(sys.argv[2]).set_index("id")
b = b.loc[a.index]                      # stesse domande, stesso ordine

diff = (a.f1 - b.f1).to_numpy() * 100
res = bootstrap((diff,), np.mean, n_resamples=10000, method="percentile",
                paired=False, random_state=1, confidence_level=0.95)
lo, hi = res.confidence_interval
p_w = wilcoxon(a.f1, b.f1).pvalue if (diff != 0).any() else 1.0

n_only_a = int(((a.em == 1) & (b.em == 0)).sum())
n_only_b = int(((a.em == 0) & (b.em == 1)).sum())
p_mc = mcnemar([[0, n_only_a], [n_only_b, 0]],
               exact=(n_only_a + n_only_b) < 25).pvalue

print(f"n = {len(a)}")
print(f"macro F1 A = {a.f1.mean()*100:.2f}   macro F1 B = {b.f1.mean()*100:.2f}")
print(f"diff A-B  = {diff.mean():+.2f}  IC95% [{lo:+.2f}, {hi:+.2f}]")
print(f"Wilcoxon p = {p_w:.4f}")
print(f"McNemar: solo A giusta = {n_only_a}, solo B giusta = {n_only_b}, p = {p_mc:.4f}")
for ho in (False, True):
    m = a.held_out == ho
    d = (a.f1[m] - b.f1[m]).to_numpy() * 100
    r = bootstrap((d,), np.mean, n_resamples=10000, method="percentile",
                  random_state=1).confidence_interval
    print(f"held_out={ho}: n={m.sum()}  diff={d.mean():+.2f}  IC95% [{r[0]:+.2f}, {r[1]:+.2f}]")
