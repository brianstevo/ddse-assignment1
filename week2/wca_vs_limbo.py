#!/usr/bin/env python3
"""
Compare WCA UEMNM vs Limbo IL across all k values.
Computes A2a + strict CVG, one direction per pair.
"""

import subprocess, shutil
from pathlib import Path
from collections import defaultdict

BASE      = Path(__file__).parent
REPO      = BASE.parent
TOOLS     = REPO / "tools"
A2A_JAR   = TOOLS / "arcade_core_A2a.jar"
CVG_JAR   = TOOLS / "arcade_core_Cvg.jar"
WCA_DIR   = REPO / "week1/wca"
LIMBO_DIR = REPO / "week1/limbo"
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
    wca_files   = {k: WCA_DIR   / f"WCA_UEMNM_{k}.rsf" for k in K_VALUES}
    limbo_files = {k: LIMBO_DIR / f"Limbo_IL_{k}.rsf"  for k in K_VALUES}

    rows = []
    seen = set()

    for kw in K_VALUES:
        for kl in K_VALUES:
            ra, rb = wca_files[kw], limbo_files[kl]
            if not ra.exists() or not rb.exists():
                print(f"  MISSING: {ra.name} or {rb.name}")
                continue

            pair = (f"WCA UEMNM {kw}", f"Limbo IL {kl}")
            rev  = (pair[1], pair[0])
            if rev in seen:
                continue

            score = run_a2a(ra, rb)
            if score is None: continue
            cvg = run_cvg_strict(ra, rb)
            rows.append((*pair, score, cvg))
            seen.add(pair)
            print(f"  {pair[0]:<20} vs {pair[1]:<20} A2a={score:.2f} CVG={cvg}")

    rows.sort(key=lambda r: r[2], reverse=True)

    table_path = BASE / "wca_vs_limbo.txt"
    hdr = f"{'WCA':<22} {'Limbo':<22} {'A2A':>7} {'CVG':>6}"
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
