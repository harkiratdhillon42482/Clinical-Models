# Project 2 — Liver Deterioration Prediction (v2)

## XGBoost Model for Liver Transplant Candidate Identification

> ⚠️ **RESEARCH ONLY — NOT FOR CLINICAL USE**

---

## v2 Update — Three Pipeline Fixes Applied

Based on expert peer review, three critical fixes were implemented:

### Fix 1 — ED Lab Time-Window (Critical)
**Root cause of the 16% admission gap identified and fixed.**

MIMIC-IV stores 46.6% of lab events with `hadm_id = NULL` — these are
labs drawn in the Emergency Department before formal admission. The original
pipeline filtered them out with `WHERE hadm_id IS NOT NULL`, silently
dropping 73.7M labs including MELD-critical values.

**Fix:** Replace `hadm_id` join with 12-hour pre-admission time-window:
```sql
-- Before (drops ED labs)
WHERE l.valuenum IS NOT NULL AND l.hadm_id IS NOT NULL

-- After (captures ED labs)
JOIN admissions a ON l.subject_id = a.subject_id
AND l.charttime BETWEEN a.admittime - INTERVAL '12 hours' AND a.dischtime
WHERE l.valuenum IS NOT NULL
```

**Impact:** +184 liver admissions MELD-scored, ICU AUC improved 0.778→0.789 (+0.011)

### Fix 2 — Proper YottaDB Error Handling
Replaced bare `except` blocks that silently returned `None` on any error.
Now distinguishes `YDBNodeEnd` (expected missing node) from `YDBError`
(real database error that must propagate).

### Fix 3 — Safe Field Delimiter
Replaced `^` field separator with `\x1F` (ASCII Unit Separator).
The `^` character appears in clinical text (diagnosis titles, notes)
causing field-shift bugs in downstream parsing.

---

## Key Results (v2 — Post Fix)

### MIMIC-III Training (2001-2012, ICU only)

| Model | AUC | 95% CI | F1 |
|-------|-----|--------|----|
| **XGBoost** ★ | **0.853** | [0.818, 0.884] | 0.587 |
| LightGBM | 0.847 | [0.812, 0.880] | 0.567 |
| Gradient Boosting | 0.829 | [0.792, 0.863] | 0.556 |
| Ghandian 2022 (reference) | 0.871 | [0.859, 0.882] | — |

### MIMIC-IV Temporal Validation (2008-2019) — v2

| Experiment | Pairs | AUC | v1→v2 |
|-----------|-------|-----|-------|
| All 2008-2019 | 9,540 | **0.8108** | +0.002 |
| Early 2008-2013 | 6,852 | 0.8101 | +0.002 |
| Post 2014-2019 | 2,688 | 0.8080 | +0.002 |
| **ICU only** | 1,215 | **0.7893** | **+0.011** |
| Ward only | 8,325 | 0.8157 | stable |

### Ground Truth Verification

| Risk Category | Admissions | Deteriorated | Rate |
|--------------|------------|--------------|------|
| Very High (>0.7) | 551 | 243 | **44.1%** |
| High (0.5-0.7) | 351 | 92 | 26.2% |
| Moderate (0.3-0.5) | 446 | 104 | 23.3% |
| Low (<0.3) | 3,264 | 351 | **10.8%** |

**4.1× risk gradient.** 334 flagged. 232 true positives (69.5%).

---

## Methodology

### Prediction Task
At admission N, predict deterioration at admission N+1 using only
data available at admission N (no future leakage).

### Option C Composite Label
Label = 1 if ANY:
1. MELD-Na increases ≥ 5 points
2. MELD-Na reaches ≥ 30
3. New hepatorenal syndrome
4. New hepatic encephalopathy
5. Bleeding esophageal varices
6. Death at next admission

### MELD-Na Computation (v2 — time-window)
```
Labs: peak bilirubin + peak creatinine within 12h pre-admission to discharge
      last INR + last sodium in same window
MELD = 3.78×ln(bili) + 11.2×ln(INR) + 9.57×ln(creat) + 6.43
MELD-Na = MELD + 1.32×(137-Na) - 0.033×MELD×(137-Na)
Bounds: MELD-Na ∈ [6, 40]
```

### Evaluation Rigor
Three runs were needed to reach honest AUC:
- Run 1 (label leakage): AUC 0.984 — DISCARDED
- Run 2 (same-patient split): AUC 0.956 — DISCARDED
- Run 3 (patient-level split, no leakage): AUC **0.853** — PUBLISHED

---

## Real Patients Verified

| Patient | Score | Diagnosis | Outcome | Correct? |
|---------|-------|-----------|---------|----------|
| 11345335 | 0.997 | Alcoholic cirrhosis | DIED — hepatorenal | ✓ |
| 10944305 | 0.996 | Hepatorenal syndrome | DIED — creat 4.5→6.7 | ✓ |
| 10670524 | 0.995 | Varices + hepatorenal | DIED — creat 1.3→11.9 | ✓ |
| 11004856 | 0.985 | Post-transplant graft | DIED | ✓ |
| 10916044 | 0.997 | Liver cell carcinoma | DIED same day | ✓ |
| 10382575 | 0.988 | Alcoholic hepatitis | Survived (ICU) | ~ |

---

## Files

```
scripts/
  liver_pg.py            MIMIC-III Postgres feature extraction
  liver_ydb.py           MIMIC-III MUMPS feature extraction
  liver_pg_v2.py         MIMIC-IV feature extraction (v2 with ED fix)
  xgboost_liver.py       Model training and evaluation
  compare_liver.py       5-model comparison
  label_option_c.py      Option C composite label
  tokenizer.py           LLM tokenizer (Phase 3)

sql/
  06_ground_truth_verification.sql

docs/
  index.html             Results dashboard (v2)
  paper.html             Full paper
  model_card.html        77 features, parameters, decision logic
```

---

## Phases

- **Phase 1** ✅ XGBoost MIMIC-III — AUC 0.853
- **Phase 2** ✅ MIMIC-IV temporal validation — AUC 0.811 (v2)
- **Phase 3** 🔄 LSTM sequence model — expected AUC 0.87-0.92
- **Phase 4** 📋 Transformer 50-60M params — expected AUC 0.90-0.95
- **Phase 5** 📋 Live HL7 v2.9 ADT feed

---

## Data Requirements

MIMIC data is NOT included. See LICENSE.md for full PhysioNet DUA requirements.
Obtain credentials at https://physionet.org
