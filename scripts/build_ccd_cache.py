"""Build a local CCD district enrollment cache for the web app.

This script uses the Urban Institute Education Data Portal CCD endpoints.
Run from the project root:
    python scripts/build_ccd_cache.py

Output:
    ccd_district_enrollment_2015_2024.json
"""
from __future__ import annotations
import json, time, urllib.parse, urllib.request
from pathlib import Path

YEARS = range(2015, 2025)
API = "https://educationdata.urban.org/api/v1/school-districts/ccd"
OUT = Path("ccd_district_enrollment_2015_2024.json")

def get_json(url: str):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def rows(obj):
    if isinstance(obj, list): return obj
    return obj.get("results") or obj.get("data") or obj.get("records") or []

def first(row, names):
    for n in names:
        v = row.get(n)
        if v not in (None, "", -1, -2, -9): return v
    return None

def enrollment_value(row):
    v = first(row, ["enrollment", "member", "membership", "students", "student_count", "count", "total", "tot_enrollment"])
    return None if v is None else int(float(v))

def get_directory(year=2024):
    data = rows(get_json(f"{API}/directory/{year}/"))
    districts = []
    for r in data:
        leaid = str(first(r, ["leaid", "LEAID", "ncesid", "district_id", "agency_id"]) or "").zfill(7)
        name = first(r, ["lea_name", "leaid_name", "district_name", "agency_name", "name", "leanm", "LEA_NAME", "NAME"])
        state = first(r, ["state", "state_abbr", "stabbr", "STABBR", "state_code", "fips"])
        if leaid and name:
            districts.append({"leaid": leaid, "name": name, "state": state})
    return districts

def get_enrollment(leaid: str, year: int):
    candidates = [
        f"{API}/enrollment/{year}/grade-all/?leaid={urllib.parse.quote(leaid)}",
        f"{API}/enrollment/{year}/grade-total/?leaid={urllib.parse.quote(leaid)}",
        f"{API}/enrollment/{year}/?leaid={urllib.parse.quote(leaid)}",
    ]
    for url in candidates:
        try:
            vals = [enrollment_value(r) for r in rows(get_json(url))]
            vals = [v for v in vals if v is not None]
            if vals: return sum(vals)
        except Exception:
            pass
    grades = ["grade-pk","grade-kg","grade-1","grade-2","grade-3","grade-4","grade-5","grade-6","grade-7","grade-8","grade-9","grade-10","grade-11","grade-12","grade-13","ungraded"]
    total = 0; ok = False
    for g in grades:
        try:
            vals = [enrollment_value(r) for r in rows(get_json(f"{API}/enrollment/{year}/{g}/?leaid={urllib.parse.quote(leaid)}"))]
            vals = [v for v in vals if v is not None]
            if vals:
                total += sum(vals); ok = True
        except Exception:
            continue
    return total if ok else None

def main():
    districts = get_directory(2024)
    print(f"Loaded {len(districts):,} districts")
    out = []
    for i, d in enumerate(districts, 1):
        d["enrollment"] = {str(y): get_enrollment(d["leaid"], y) for y in YEARS}
        out.append(d)
        if i % 100 == 0:
            print(f"{i:,}/{len(districts):,}")
            OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
        time.sleep(0.05)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
