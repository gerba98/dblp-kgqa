# Reproducibility material

This directory contains the configuration files, aggregate metrics, statistical-analysis scripts and results of the experiments reported in:

> N. Capuano, L. Gerbasi, S. Senatore. *Ontology-Aware Context Selection for LLM-Based SPARQL Generation under Gold Grounding: Template Generalization on DBLP-QuAD*. Submitted to the Journal of Web Semantics.

The per-question outputs of all runs (`exp_results.json`, `experiment.log`), the per-question score files, the chain-of-thought traces of the training examples and the precomputed embeddings are too large for git and are archived on Zenodo: **[DOI: 10.5281/zenodo.23991429](https://doi.org/10.5281/zenodo.23991429)**.

Prompts and code are in `src/dblp_kgqa/` (prompts in `modules/query_generator/llm_prompt.py`; full-schema predicate list in `modules/relation_linker/full_schema.py`).

## Contents

```
reproducibility/
├── runs/<run>/                 one directory per run (35 runs)
│   ├── exp_config.yml          pipeline configuration
│   ├── services.yml            model and service configuration
│   └── qa_metrics.csv          aggregate metrics computed by evaluate.py
├── analysis/                   statistical-analysis scripts
│   ├── extract_scores.py       per-question scores from exp_results.json
│   ├── analyze_all.py          paired contrasts, breakdowns, retriever analysis
│   ├── splithalf.py            cross-fitted configuration selection
│   ├── stat_tests.py           paired comparison of two runs
│   ├── verify.py               independent check of one contrast
│   ├── tp32_sensitivity.py     sensitivity analysis for template TP32
│   └── requirements.txt
└── results/
    ├── statistical_analysis.xlsx      all statistics reported in the paper
    └── tp32_sensitivity/
        ├── excluded/                  same analyses without the 25 TP32 questions
        └── corrected/                 same analyses with corrected TP32 gold answers
```

The comments in the analysis scripts are in Italian.

In `services.yml`, the addresses of the remote GPU pods used for the local models have been replaced by `<runpod-pod-id>`; no other change was made to the configuration files.

## Experimental setting common to all runs

- DBLP-QuAD test split (2,000 questions); gold query types and entity URIs (`GoldInfoExtractor`, `GoldEntityLinker`).
- Evaluation against a local Virtuoso endpoint loaded with the DBLP RDF dump of 1 August 2022.
- Embeddings: `gemini-embedding-001`; temperature 0.
- Relation Linker: the RAG configurations index the DBLP ontology version 2022-03-02 (https://dblp.org/rdf/schema-2022-03-02, 54 predicates after removing `authorOf`, `creatorOf`, `editorOf`); the full-schema configurations use the list in `full_schema.py`, derived from version 2024-06-14 (https://dblp.org/rdf/schema-2024-06-14, 75 predicates after the same removal).
- Cloud model: `gemini-3.1-flash-lite-preview`. Local model: Qwen3.5-4B (UD-Q4_K_XL). Auxiliary run: Qwen2.5-Coder-32B-Instruct (Q8_0).

## Runs

Abbreviations: FS full schema; RAG predicate retrieval with $m$ predicates; DR domain-range enrichment; SFS static few-shot examples; DFS dynamic few-shot retrieval with $k$ examples; CoT chain-of-thought; FQT query-type filtering.

| Run (directory suffix) | Model | Schema | m | DR | SFS | CoT | DFS k | FQT |
|---|---|---|---|---|---|---|---|---|
| `Gem_I` | Gemini | FS | – | – | no | no | – | – |
| `Gem_II` | Gemini | FS | – | – | no | yes | – | – |
| `Gem_III` | Gemini | FS | – | – | yes | no | – | – |
| `Gem_IV` | Gemini | FS | – | – | yes | yes | – | – |
| `Gem_V` | Gemini | FS | – | – | no | no | 5 | no |
| `Gem_VI` | Gemini | FS | – | – | no | no | 5 | yes |
| `Gem_VII` | Gemini | FS | – | – | no | yes | 5 | no |
| `Gem_VIII` | Gemini | FS | – | – | no | yes | 5 | yes |
| `Gem_IX` | Gemini | FS | – | – | yes | yes | 5 | yes |
| `Gem_VIII_DFS3` | Gemini | FS | – | – | no | yes | 3 | yes |
| `Gem_VIII_DFS10_best` | Gemini | FS | – | – | no | yes | 10 | yes |
| `Gem_VIII_DFS15` | Gemini | FS | – | – | no | yes | 15 | yes |
| `Gem_X_DFS10` | Gemini | RAG | 10 | no | no | yes | 10 | yes |
| `Gem_X_DFS10_RRR15` | Gemini | RAG | 15 | no | no | yes | 10 | yes |
| `Gem_X_DFS10_RRR20` | Gemini | RAG | 20 | no | no | yes | 10 | yes |
| `Gem_XI_DFS10_DR` | Gemini | RAG | 10 | yes | no | yes | 10 | yes |
| `Gem_XI_DFS10_RRR20_DR` | Gemini | RAG | 20 | yes | no | yes | 10 | yes |
| `Qwen_I` … `Qwen_IX` | Qwen3.5-4B | as `Gem_I` … `Gem_IX` | | | | | | |
| `Qwen_VIII_DFS3` | Qwen3.5-4B | FS | – | – | no | yes | 3 | yes |
| `Qwen_VIII_DFS10` | Qwen3.5-4B | FS | – | – | no | yes | 10 | yes |
| `Qwen_VIII_DFS15` | Qwen3.5-4B | FS | – | – | no | yes | 15 | yes |
| `Qwen_X_DFS15` | Qwen3.5-4B | RAG | 10 | no | no | yes | 15 | yes |
| `Qwen_X_DFS15_RRR15` | Qwen3.5-4B | RAG | 15 | no | no | yes | 15 | yes |
| `Qwen_X_DFS15_RRR20_best` | Qwen3.5-4B | RAG | 20 | no | no | yes | 15 | yes |
| `Qwen_XI_DFS15_DR` | Qwen3.5-4B | RAG | 10 | yes | no | yes | 15 | yes |
| `Qwen_XI_DFS15_RRR20_DR` | Qwen3.5-4B | RAG | 20 | yes | no | yes | 15 | yes |
| `Qwen25Coder_X_DFS15_RRR20_ask-dblp` | Qwen2.5-Coder-32B | RAG | 20 | no | no | yes | 15 | yes |

The exact settings of each run are in its `exp_config.yml` and `services.yml`.

## Reproducing the statistics

No model is called in these steps. Python 3.14 was used; install the dependencies with `pip install -r analysis/requirements.txt`.

1. Download the per-question outputs from Zenodo and extract them so that each run directory contains its `exp_results.json`. The Zenodo archive also contains the per-question score files (`scores/`): with those, step 2 can be skipped.
2. Compute the per-question scores (the DBLP-QuAD test `questions.json` and `answers.json` are downloaded by `scripts/init_data.py` into `data/dblp_quad/test`):

   ```bash
   python analysis/extract_scores.py --root <runs-directory> --data data/dblp_quad/test
   ```

3. Recompute all statistics of the paper (paired bootstrap, Wilcoxon, McNemar, non-inferiority, breakdowns by query type and seen/held-out templates, retriever analysis) and the cross-fitted selection:

   ```bash
   python analysis/analyze_all.py --scores scores --out statistical_analysis.xlsx
   python analysis/splithalf.py --scores scores --repeats 20 --out splithalf_selection.csv
   ```

   The output reproduces `results/statistical_analysis.xlsx`. In one of the 80 cross-fitted selections (seed 13, cloud model, RAG-only pool) two configurations are tied and the selected one may differ; no figure reported in the paper depends on it.

4. Sensitivity analysis for template TP32 (see below):

   ```bash
   python analysis/tp32_sensitivity.py --mode exclude --scores scores --questions data/dblp_quad/test/questions.json --out scores_tp32_excluded
   python analysis/tp32_sensitivity.py --mode correct --scores scores --questions data/dblp_quad/test/questions.json --runs <runs-directory> --out scores_tp32_corrected
   ```

   and then run step 3 on each output directory. The results are in `results/tp32_sensitivity/`.

## Template TP32

The 25 test questions of DBLP-QuAD template TP32 are BOOLEAN questions whose gold queries use `dcterms:bibtexType`, a predicate that does not occur in the DBLP knowledge graph, instead of `dblp:bibtexType`. Their official gold answers are therefore always `false`. The 276 queries generated across the runs that use `dblp:bibtexType` with the publication type asked in the question cover all 25 questions and all return `true` on the evaluation dump. The main results use the official gold answers; `results/tp32_sensitivity/` reports the same analyses excluding these questions and with their gold answers corrected to `true`.
