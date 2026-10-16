"""Rebuild notebooks/evaluation.ipynb from source cells. Run from the repository root, then execute with nbconvert."""
import nbformat as nbf
nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
md("""# Evaluation: Food Decision Intelligence (methodology v0.1.0)

This notebook runs every evaluation the available labelled data allows and states plainly what could not run.
**Read the sample sizes.** The labelled sets are small, team-labelled and partly synthetic
(`data/verified/eval/README.md`), so these numbers show that the evaluation code works and give a first signal.
They are not accuracy claims about real products. The build spec's target of a 100–200 product verified set is a
target, not a result.

Run from the repository root: `jupyter nbconvert --to notebook --execute notebooks/evaluation.ipynb`.
The same code runs headless with `PYTHONPATH=src python -m evaluation.run`."""),
code("""import sys, json, pathlib
ROOT = pathlib.Path.cwd() if (pathlib.Path.cwd() / 'src').exists() else pathlib.Path.cwd().parent
sys.path.insert(0, str(ROOT / 'src'))
import pandas as pd
pd.set_option('display.precision', 3)
from evaluation import run as ev
results = ev.run_all(write=True)
print('methodology', results['methodology_version'])"""),
md("## 1. Extraction: precision, recall, exact-match accuracy\nField-level comparison against hand-read values for the four synthetic test pages. Numeric values match within 2 %. The fourth page has no structured data, so with no LLM key the deterministic extractors find nothing there; that page is what the optional LLM fallback is for."),
code("""e = results['extraction']
print(e['data']); print('pages:', e['n_pages'], ' fields:', e['overall']['n_fields'])
display(pd.DataFrame([e['overall']]))
display(pd.DataFrame(e['per_page']).T[['n_fields','precision','recall','exact_match_accuracy']])
display(pd.DataFrame(e['per_field']).T[['precision','recall','exact_match_accuracy']])"""),
md("## 2. Ingredient classification: precision, recall, F1\nTop class per ingredient phrase against team labels. `uncertain` means the system declined to classify; it counts as no label (a missed class is a false negative, not a false positive). **Caveat:** the same team wrote the ingredient dictionary and these labels, so a perfect score here mostly shows the dictionary and parser agree with the team's own definitions; it says little about unseen real labels."),
code("""i = results['ingredients']
print(i['data']); print('items:', i['n_items'])
display(pd.DataFrame([i['classification']]))
print('uncertainty flag (expected uncertain vs flagged uncertain):')
display(pd.DataFrame([i['uncertainty_flag']]))
print('errors:', i['errors'] or 'none')"""),
md("## 3. Claim checks: precision, recall, false-positive rate\nExpected statuses were worked out by hand from the FSSAI conditions before running the code. The positive class is *potential inconsistency for review*. **Caveat:** 22 hand-built cases test that the rules are implemented as written; they do not measure performance on real listings, where claim wording and missing data vary far more."),
code("""c = results['claims']
print(c['data']); print('cases:', c['n_cases'], ' status accuracy:', round(c['status_accuracy'], 3))
display(pd.DataFrame([c['inconsistency_detection']]))
print('disagreements:', c['disagreements'] or 'none')"""),
md("## 4. Product matching: correct-match rate\nThe matcher links a new listing to a stored Open Food Facts record (reference only). Queries are perturbed names of the synthetic sample plus products that are not stored (correct answer: no match)."),
code("""m = results['product_matching']
print(m['data']); print('queries:', m['n_queries'], ' correct-match rate:', round(m['correct_match_rate'], 3))
display(pd.DataFrame(m['by_perturbation']).T)"""),
md("## 5. Scoring against Nutri-Score and expert rankings\nSpearman rank correlation between the nutrition score N and the Open Food Facts Nutri-Score grade (A=5 … E=1) for real India records that have both. Nutri-Score is an independently designed scheme and a reference point, not ground truth, so agreement is a check of direction, not a target to maximise. Full write-up with sample selection, missing data and limits: `docs/nutriscore_comparison.md`."),
code("""from evaluation import nutriscore
ns = nutriscore.main()   # also writes reports/nutriscore_comparison.json
print('funnel:', ns['funnel'])
print('n =', ns['n_products'], ' Spearman', ns['spearman'], ns['spearman_95ci'], ' Kendall tau-b', ns['kendall_tau_b'], ns['kendall_95ci'])
display(pd.DataFrame(ns['by_category']).T[['n', 'spearman', 'spearman_95ci']])
display(pd.DataFrame(ns['n_by_nutriscore_grade']).T)
print('N band vs Nutri-Score grade (rows: Nutri-Score)')
display(pd.DataFrame(ns['band_agreement']['rows_nutriscore_cols_n_band']).T)
print(json.dumps(results['expert_ranking'], indent=1))"""),
md("""## 5b. Real-data coverage (Open Food Facts India)
What the pipeline can do with the 2,692 real OFF India records in the five categories (full extract in `data/raw/off_india.jsonl`, made with `scripts/off_export_to_jsonl.py`). This measures coverage, not accuracy. **Caveat:** the ingredient dictionary was expanded on 12 Oct 2026 from the most frequent unclassified terms in this same data, so the uncertain share is an in-sample figure."""),
code("""cov = results['real_data_coverage']
print(json.dumps({k: cov[k] for k in cov if k not in ('share_missing_by_field',)}, indent=1))
display(pd.Series(cov.get('share_missing_by_field', {}), name='share missing').to_frame())"""),
md("## 6. Recommendations: Precision@3 and NDCG@5"),
code("""print(json.dumps(results['recommendations'], indent=1))
from evaluation.metrics import precision_at_k, ndcg_at_k
# The metric functions are ready; example on a toy ranking (not a result):
print('toy example only:', precision_at_k(['a','b','c'], {'a','c'}, 3), round(ndcg_at_k(['b','a'], {'a':3,'b':1}), 3))"""),
md("## 7. Robustness\n**Weight sensitivity:** each dimension weight scaled by 0.8 or 1.2 (then renormalised). **Missing fields:** one nutrient removed at a time; *overall_not_computed* counts products whose nutrition coverage fell below 50 %, so no grade is given instead of a guessed one. **Conflicting sources:** a second source with changed values must be flagged when the difference is over 2 %."),
code("""r = results['robustness']
print(r['weights']['data']); display(pd.DataFrame(r['weights']['perturbations']).T)
print(r['missing_fields']['data']); display(pd.DataFrame(r['missing_fields']['by_nutrient']).T)
print(r['conflicting_sources']['data'], '- cases:', r['conflicting_sources']['n_cases'])
display(pd.DataFrame([r['conflicting_sources']['detection']]))"""),
md("## 8. Targets not yet met"),
code("""for t in results['targets_not_yet_met']: print('-', t)"""),
]
nb["cells"] = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "notebooks/evaluation.ipynb")
