import os, sys, time, psycopg2
from datetime import datetime
from collections import defaultdict

os.environ["ydb_gbldir"] = "/data/r2.06_x86_64/g/yottadb.gld"
import yottadb as ydb

PG_IV = {"host":"host.docker.internal","port":5432,
         "dbname":"MIMICIV","user":"postgres","password":"YOUR_PASSWORD_HERE"}

SRC = "MIV"

def pid_key(subject_id):
    return f"HIE-{SRC}-{int(subject_id):06d}"

def eid_key(hadm_id):
    return f"ENC-{SRC}-{int(hadm_id):08d}"

def safe(v):
    if v is None: return ""
    return str(v).replace("^","").replace("\n"," ").replace("\r","")[:200]

def ts(dt):
    if dt is None: return ""
    return str(dt)[:19]

def yset(subs, value):
    """Set ^PHD with list of subscripts"""
    ydb.set("^PHD", list(subs), str(value))

class Progress:
    def __init__(self, name, total):
        self.name = name; self.total = total
        self.count = 0; self.t0 = time.time(); self.last = time.time()
    def tick(self, n=1):
        self.count += n
        now = time.time()
        if now - self.last >= 15:
            pct  = self.count/max(self.total,1)*100
            rate = self.count/max(now-self.t0,1)
            eta  = (self.total-self.count)/max(rate,1)
            print(f"  {self.name}: {self.count:,}/{self.total:,} "
                  f"({pct:.1f}%) {rate:.0f}/s ETA {eta/60:.1f}m",
                  flush=True)
            self.last = now
    def done(self):
        elapsed = time.time()-self.t0
        rate = self.count/max(elapsed,1)
        print(f"  DONE {self.name}: {self.count:,} in "
              f"{elapsed/60:.1f}m ({rate:.0f}/s)")

def load_patients(pg):
    print("\n[1] Loading patients (364,627)...")
    cur = pg.cursor()
    cur.execute("""
        SELECT subject_id, gender, anchor_age,
               anchor_year, anchor_year_group, dod
        FROM hosp.patients ORDER BY subject_id
    """)
    rows = cur.fetchall(); cur.close()
    p = Progress("patients", len(rows))
    for subject_id, gender, age, anchor_year, ayg, dod in rows:
        pid = pid_key(subject_id)
        yset([pid,"SRC"], SRC)
        yset([pid,"PID"],
             f"{subject_id}^{safe(gender)}^{safe(age)}^"
             f"{safe(anchor_year)}^{safe(ayg)}^{safe(dod)}")
        yset(["BSRC",SRC,str(subject_id),pid], "1")
        p.tick()
    p.done()

def load_admissions(pg):
    print("\n[2] Loading admissions (546,028)...")
    cur = pg.cursor()
    cur.execute("""
        SELECT a.subject_id, a.hadm_id,
               a.admittime, a.dischtime,
               a.admission_type, a.insurance,
               a.hospital_expire_flag,
               EXTRACT(EPOCH FROM
                   (a.dischtime-a.admittime))/3600 AS los_hours,
               CASE WHEN i.hadm_id IS NOT NULL
                    THEN 1 ELSE 0 END AS had_icu
        FROM hosp.admissions a
        LEFT JOIN (SELECT DISTINCT hadm_id FROM icu.icustays) i
            ON a.hadm_id=i.hadm_id
        ORDER BY a.subject_id, a.admittime
    """)
    rows = cur.fetchall(); cur.close()
    p = Progress("admissions", len(rows))
    for (subject_id, hadm_id, admittime, dischtime,
         adm_type, insurance, expire_flag,
         los_hours, had_icu) in rows:
        pid = pid_key(subject_id)
        eid = eid_key(hadm_id)
        yset([pid,"VISIT",eid,"0"],
             f"{ts(admittime)}^{ts(dischtime)}^"
             f"{safe(adm_type)}^^{safe(insurance)}^"
             f"{safe(expire_flag)}^^"
             f"{round(float(los_hours),1) if los_hours else ''}^"
             f"{had_icu}")
        yset(["BSRC",SRC,"ADM",str(hadm_id),pid,eid], "1")
        p.tick()
    p.done()

def load_diagnoses(pg):
    print("\n[3] Loading diagnoses (1,048,552)...")
    cur = pg.cursor()
    cur.execute("""
        SELECT d.subject_id, d.hadm_id, d.seq_num,
               d.icd_code, d.icd_version,
               COALESCE(di.long_title,'') AS title
        FROM hosp.diagnoses_icd d
        LEFT JOIN hosp.d_icd_diagnoses di
            ON d.icd_code=di.icd_code
            AND d.icd_version=di.icd_version
        ORDER BY d.subject_id, d.hadm_id, d.seq_num
    """)
    p = Progress("diagnoses", 1048552)
    batch = 100000
    while True:
        rows = cur.fetchmany(batch)
        if not rows: break
        by_adm = defaultdict(list)
        for row in rows:
            by_adm[(row[0], row[1])].append(row)
        for (subject_id, hadm_id), dx_rows in by_adm.items():
            pid = pid_key(subject_id)
            eid = eid_key(hadm_id)
            for r in dx_rows:
                yset([pid,"VISIT",eid,"DX",str(r[2])],
                     f"{safe(r[3])}^{safe(r[4])}^{safe(r[5])}^{r[2]}")
            p.tick(len(dx_rows))
    cur.close()
    p.done()

def load_medications(pg):
    print("\n[4] Loading medications (20,292,611)...")
    print("    Estimated time: 30-45 minutes")
    cur = pg.cursor()
    cur.execute("""
        SELECT subject_id, hadm_id, drug, gsn,
               route, dose_val_rx, dose_unit_rx,
               starttime, stoptime, drug_type
        FROM hosp.prescriptions
        WHERE drug IS NOT NULL
        ORDER BY subject_id, hadm_id, starttime
    """)
    p = Progress("medications", 20292611)
    counters = defaultdict(int)
    batch = 500000
    while True:
        rows = cur.fetchmany(batch)
        if not rows: break
        by_adm = defaultdict(list)
        for row in rows:
            by_adm[(row[0], row[1])].append(row)
        for (subject_id, hadm_id), med_rows in by_adm.items():
            if hadm_id is None: continue
            pid = pid_key(subject_id)
            eid = eid_key(hadm_id)
            key = (pid, eid)
            for (sid, hid, drug, gsn, route,
                 dose_val, dose_unit,
                 starttime, stoptime, drug_type) in med_rows:
                counters[key] += 1
                n = counters[key]
                yset([pid,"VISIT",eid,"MED",str(n)],
                     f"{safe(drug)}^{safe(gsn)}^{safe(drug_type)}^"
                     f"{safe(dose_val)}^{safe(dose_unit)}^{safe(route)}^"
                     f"{ts(starttime)}^{ts(stoptime)}")
            p.tick(len(med_rows))
    cur.close()
    p.done()

def load_icu(pg):
    print("\n[5] Loading ICU stays (94,458)...")
    cur = pg.cursor()
    cur.execute("""
        SELECT subject_id, hadm_id, stay_id,
               first_careunit, last_careunit,
               intime, outtime, los
        FROM icu.icustays
        ORDER BY subject_id, hadm_id, intime
    """)
    rows = cur.fetchall(); cur.close()
    p = Progress("icustays", len(rows))
    for (subject_id, hadm_id, stay_id, first_cu,
         last_cu, intime, outtime, los) in rows:
        pid = pid_key(subject_id)
        eid = eid_key(hadm_id)
        yset([pid,"VISIT",eid,"ICU",str(stay_id),"0"],
             f"{safe(first_cu)}^{ts(intime)}^"
             f"{ts(outtime)}^{safe(los)}^MIV")
        p.tick()
    p.done()

def load_labs(pg):
    print("\n[6] Loading lab events (158,374,764)...")
    print("    Using server-side cursor — low memory usage")
    print("    Progress saved every 500K rows — safe to resume")

    # Get item descriptions
    cur = pg.cursor()
    cur.execute("SELECT itemid, label, fluid, category "
                "FROM hosp.d_labitems")
    item_map = {r[0]: f"{safe(r[1])}^{safe(r[2])}^{safe(r[3])}"
                for r in cur.fetchall()}
    cur.close()

    # Check resume point
    resume_file = "/tmp/lab_etl_offset.txt"
    offset = 0
    if os.path.exists(resume_file):
        with open(resume_file) as f:
            offset = int(f.read().strip())
        print(f"  Resuming from offset {offset:,}")

    p = Progress("labevents", 158374764)
    p.count = offset
    counters = defaultdict(int)
    loaded = 0

    # Server-side cursor — Postgres streams rows, no RAM spike
    cur = pg.cursor("lab_cursor")
    cur.itersize = 10000
    cur.execute("""
        SELECT subject_id, hadm_id, itemid,
               valuenum, valueuom, flag, charttime
        FROM hosp.labevents
        WHERE valuenum IS NOT NULL AND hadm_id IS NOT NULL
        ORDER BY subject_id, hadm_id, charttime
        OFFSET %s
    """, (offset,))

    batch = []
    batch_size = 10000

    for row in cur:
        batch.append(row)
        if len(batch) >= batch_size:
            by_adm = defaultdict(list)
            for r in batch:
                by_adm[(r[0], r[1])].append(r)
            for (subject_id, hadm_id), lab_rows in by_adm.items():
                pid = pid_key(subject_id)
                eid = eid_key(hadm_id)
                key = (pid, eid)
                for (sid, hid, itemid, valuenum,
                     uom, flag, charttime) in lab_rows:
                    counters[key] += 1
                    n = counters[key]
                    item_desc = item_map.get(itemid, f"{itemid}^^")
                    yset([pid,"VISIT",eid,"LAB",str(n)],
                         f"{itemid}^{safe(valuenum)}^{safe(uom)}^"
                         f"{safe(flag)}^{ts(charttime)}^{item_desc}")
            loaded += len(batch)
            p.tick(len(batch))
            # Save progress every 500K rows
            if loaded % 500000 < batch_size:
                with open(resume_file, "w") as f:
                    f.write(str(offset + loaded))
            batch = []

    # Process remaining rows
    if batch:
        by_adm = defaultdict(list)
        for r in batch:
            by_adm[(r[0], r[1])].append(r)
        for (subject_id, hadm_id), lab_rows in by_adm.items():
            pid = pid_key(subject_id)
            eid = eid_key(hadm_id)
            key = (pid, eid)
            for (sid, hid, itemid, valuenum,
                 uom, flag, charttime) in lab_rows:
                counters[key] += 1
                n = counters[key]
                item_desc = item_map.get(itemid, f"{itemid}^^")
                yset([pid,"VISIT",eid,"LAB",str(n)],
                     f"{itemid}^{safe(valuenum)}^{safe(uom)}^"
                     f"{safe(flag)}^{ts(charttime)}^{item_desc}")
        loaded += len(batch)
        p.tick(len(batch))

    cur.close()
    if os.path.exists(resume_file):
        os.remove(resume_file)
    p.done()

def load_output_events(pg):
    print("\n[7] Loading output events (5,359,395)...")
    cur = pg.cursor()
    cur.execute("""
        SELECT o.subject_id, i.hadm_id,
               o.stay_id, o.itemid,
               o.value, o.valueuom, o.charttime
        FROM icu.outputevents o
        JOIN icu.icustays i ON o.stay_id=i.stay_id
        WHERE o.value IS NOT NULL
        ORDER BY o.subject_id, i.hadm_id, o.charttime
    """)
    p = Progress("outputevents", 5359395)
    counters = defaultdict(int)
    batch = 200000
    while True:
        rows = cur.fetchmany(batch)
        if not rows: break
        by_adm = defaultdict(list)
        for row in rows:
            by_adm[(row[0], row[1])].append(row)
        for (subject_id, hadm_id), out_rows in by_adm.items():
            if hadm_id is None: continue
            pid = pid_key(subject_id)
            eid = eid_key(hadm_id)
            key = (pid, eid)
            for (sid, hid, stay_id, itemid,
                 value, uom, charttime) in out_rows:
                counters[key] += 1
                n = counters[key]
                yset([pid,"VISIT",eid,"OUT",str(n)],
                     f"{itemid}^{safe(value)}^{safe(uom)}^{ts(charttime)}")
            p.tick(len(out_rows))
    cur.close()
    p.done()

def print_summary(t_total):
    print(f"\n{'='*60}")
    print(f"  MIMIC-IV ETL Complete")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total time: {(time.time()-t_total)/3600:.2f} hours")
    print(f"{'='*60}")
    print(f"  ^PHD now contains:")
    print(f"  MIMIC-III: ^PHD(\"HIE-MIII-*\", ...)")
    print(f"  MIMIC-IV:  ^PHD(\"HIE-MIV-*\",  ...)")

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", nargs="+",
        choices=["patients","admissions","diagnoses",
                 "medications","icu","labs","output","all"],
        default=["all"])
    args = parser.parse_args()
    steps = args.steps
    if "all" in steps:
        steps = ["patients","admissions","diagnoses",
                 "medications","icu","labs","output"]
    print("="*60)
    print(f"  MIMIC-IV ETL → YottaDB ^PHD")
    print(f"  Steps: {', '.join(steps)}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    pg = psycopg2.connect(**PG_IV)
    t_total = time.time()
    step_fns = {
        "patients":    load_patients,
        "admissions":  load_admissions,
        "diagnoses":   load_diagnoses,
        "medications": load_medications,
        "icu":         load_icu,
        "labs":        load_labs,
        "output":      load_output_events,
    }
    for step in steps:
        step_fns[step](pg)
    pg.close()
    print_summary(t_total)

if __name__ == "__main__":
    main()

