#!/usr/bin/env python3
"""
Compute A2a + strict CVG for all cross-algorithm pairs (WCA, Limbo, ACDC).
Reads existing RSF files from week1/. Run week1/run_clustering.py first.
"""

import subprocess
from pathlib import Path
from collections import defaultdict

BASE      = Path(__file__).parent
REPO      = BASE.parent
TOOLS     = REPO / "tools"
A2A_JAR   = TOOLS / "arcade_core_A2a.jar"
CVG_JAR   = TOOLS / "arcade_core_Cvg.jar"
WCA_OUT   = REPO / "week1/wca"
LIMBO_OUT = REPO / "week1/limbo"
ACDC_OUT  = REPO / "week1/acdc"
K_VALUES  = [5, 10, 20, 30, 40, 50]


def run_a2a(ra, rb):
    r = subprocess.run(["java", "-jar", str(A2A_JAR), str(ra), str(rb)],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        try: return float(line.strip())
        except: pass
    return None


def run_cvg_strict(ra, rb):
    r = subprocess.run(["java", "-jar", str(CVG_JAR), str(ra), str(rb)],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        for token in line.split():
            try: return float(token)
            except: pass
    return None


def main():
    rsf_files = {}
    for k in K_VALUES:
        p = WCA_OUT / f"WCA_UEMNM_{k}.rsf"
        if p.exists(): rsf_files[f"WCA UEMNM {k}"] = p
    for k in K_VALUES:
        p = LIMBO_OUT / f"Limbo_IL_{k}.rsf"
        if p.exists(): rsf_files[f"Limbo IL {k}"] = p
    p = ACDC_OUT / "ACDC_default.rsf"
    if p.exists(): rsf_files["ACDC default"] = p

    if not rsf_files:
        print("No RSF files found. Run week1/run_clustering.py first.")
        return

    print(f"Loaded {len(rsf_files)} RSF files.")

    rows = []
    seen = set()
    keys = list(rsf_files.keys())

    for ka in keys:
        for kb in keys:
            if ka == kb: continue
            if (kb, ka) in seen: continue
            if ka.split()[0] == kb.split()[0]: continue

            ra, rb = rsf_files[ka], rsf_files[kb]
            score = run_a2a(ra, rb)
            if score is None: continue
            cvg = run_cvg_strict(ra, rb)
            rows.append((ka, kb, score, cvg))
            seen.add((ka, kb))
            print(f"  {ka:<20} vs {kb:<20} A2a={score:.2f} CVG={cvg}")

    rows.sort(key=lambda r: r[2], reverse=True)

    table_path = BASE / "a2a_cvg_comparison.txt"
    hdr = f"{'A':<22} {'B':<22} {'A2A':>7} {'CVG':>6}"
    with open(table_path, "w") as f:
        f.write(hdr + "\n")
        f.write("-" * len(hdr) + "\n")
        for ka, kb, score, cvg in rows:
            f.write(f"{ka:<22} {kb:<22} {score:>7.2f} {cvg:>6.2f}\n")

    print(f"\nSaved to {table_path}\n")
    with open(table_path) as f:
        print(f.read())


if __name__ == "__main__":
    main()
