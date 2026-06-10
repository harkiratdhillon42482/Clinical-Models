# License and Data Use Notice

---

## Part 1 — Software License (MIT)

MIT License

Copyright (c) 2026 Harkirat Dhillon

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Part 2 — Data Use Notice (MIMIC-III and MIMIC-IV)

**THIS REPOSITORY CONTAINS NO CLINICAL DATA.**

All code, scripts, SQL queries, ETL pipelines, machine learning models,
and documentation in this repository were developed using MIMIC-III and
MIMIC-IV clinical databases. The data itself is NOT included here and
is NOT available through this repository.

### Data Sources

**MIMIC-III Clinical Database**
- Full name: MIMIC-III Clinical Database v1.4
- Source: PhysioNet — https://physionet.org/content/mimiciii/1.4/
- Citation: Johnson, A., Pollard, T., Shen, L. et al. MIMIC-III, a
  freely accessible critical care database. Sci Data 3, 160035 (2016).
  https://doi.org/10.1038/sdata.2016.35

**MIMIC-IV Clinical Database**
- Full name: MIMIC-IV v2.0+
- Source: PhysioNet — https://physionet.org/content/mimiciv/
- Citation: Johnson, A.E.W., Bulgarelli, L., Shen, L. et al. MIMIC-IV,
  a freely accessible electronic health record dataset.
  Sci Data 10, 1 (2023). https://doi.org/10.1038/s41597-022-01899-x

### PhysioNet Data Use Agreement Requirements

To access MIMIC-III and MIMIC-IV you MUST:

1. **Complete CITI Training**
   Complete the required CITI Data or Specimens Only Research course
   at https://www.citiprogram.org/

2. **Register on PhysioNet**
   Create a credentialed account at https://physionet.org/register/

3. **Sign the Data Use Agreement**
   Sign the PhysioNet Credentialed Health Data Use Agreement
   separately for each dataset:
   - MIMIC-III DUA: https://physionet.org/content/mimiciii/view-dua/1.4/
   - MIMIC-IV DUA:  https://physionet.org/content/mimiciv/view-dua/

4. **Agree to the following restrictions** (from the DUA):
   - Data may be used for RESEARCH PURPOSES ONLY
   - You will NOT attempt to identify or re-identify any patient
   - You will NOT share the data with anyone who has not completed
     the above credentialing process
   - You will NOT use the data for commercial purposes
   - You will report any data breaches to PhysioNet immediately
   - Publications using these data must cite the original papers

### How to Obtain the Data

```
Step 1: Go to https://physionet.org/register/
Step 2: Complete CITI training
Step 3: Submit credentialing application (typically 1-2 days)
Step 4: Once approved, download MIMIC-III:
        https://physionet.org/content/mimiciii/1.4/
Step 5: Download MIMIC-IV:
        https://physionet.org/content/mimiciv/
Step 6: Load into PostgreSQL using official loaders:
        MIMIC-III: https://github.com/MIT-LCP/mimic-code
        MIMIC-IV:  https://github.com/MIT-LCP/mimic-iv
Step 7: Then use the ETL scripts in this repository to load
        into YottaDB ^PHD globals
```

### What IS in This Repository

```
✓ Code:    ETL scripts, ML pipeline, SQL queries
✓ Models:  Trained XGBoost model weights (.pkl)
            → These contain no patient data
            → Only mathematical parameters learned from data
✓ Results: Aggregate statistics, AUC scores, charts
            → These contain no individual patient data
✓ Docs:    Architecture documentation, methodology
✓ Config:  Database schema, Docker configuration
```

### What is NOT in This Repository

```
✗ Patient records of any kind
✗ Lab results, diagnoses, medications of individuals
✗ Any MIMIC-III or MIMIC-IV data files
✗ Any derived data that could identify a patient
✗ Database dumps or exports
```

### Research Use Only

This software and the models trained using MIMIC data are intended
for RESEARCH AND EDUCATIONAL PURPOSES ONLY.

They have NOT been:
- Approved by the FDA or any regulatory body
- Validated for clinical use
- Tested in a clinical environment
- Peer reviewed for safety

They MUST NOT be used for:
- Clinical decision making
- Patient care or treatment
- Diagnosis of any condition
- Any purpose that could affect patient outcomes

---

## Part 3 — Model Weights Notice

The trained XGBoost model weights included in this repository
(model_prospective_PG.pkl) were derived from MIMIC-III data.

These weights:
- Contain no patient data (only learned mathematical parameters)
- May be used for research and educational purposes
- Must not be used for clinical decision making
- Were trained under PhysioNet DUA restrictions
- May only be used by individuals who have agreed to the PhysioNet DUA

---

## Part 4 — Third Party Software

This project uses the following open source components:

| Software | License | URL |
|----------|---------|-----|
| YottaDB | GNU AGPL v3 | https://yottadb.com/product/open-source/ |
| PostgreSQL | PostgreSQL License | https://www.postgresql.org/about/licence/ |
| XGBoost | Apache 2.0 | https://github.com/dmlc/xgboost |
| LightGBM | MIT | https://github.com/microsoft/LightGBM |
| scikit-learn | BSD 3-Clause | https://scikit-learn.org |
| pandas | BSD 3-Clause | https://pandas.pydata.org |
| psycopg2 | LGPL | https://www.psycopg.org |
| Docker | Apache 2.0 | https://www.docker.com |

---

## Contact

For questions about this research:
Harkirat Dhillon
GitHub: https://github.com/harkiratdhillon42482

For questions about MIMIC data access:
PhysioNet: https://physionet.org/about/contact/
MIMIC team: https://mimic.mit.edu/
