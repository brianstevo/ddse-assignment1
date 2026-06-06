#!/usr/bin/env python3
"""
Compare ARC (k=5,10,20,30,40,50) vs WCA UEMNM, Limbo IL, ACDC.
Computes A2a only, one direction per pair, sorted by A2a descending.
"""

import subprocess
from pathlib import Path

BASE      = Path(__file__).parent
DSSE      = Path("/home/brian/Documents/master_cs/dsse")
ARCADE_W2 = DSSE / "assignment1/Arcade_Tools_W2"
A2A_JAR   = ARCADE_W2 / "arcade_core_A2a.jar"
CVG_JAR   = ARCADE_W2 / "arcade_core_Cvg.jar"

ARC_DIR   = BASE / "collab_output/rsf"
OTHER_DIR = DSSE / "Assignment1FinalWeek/output"
K_VALUES  = [5, 10, 20, 30, 40, 50]


def run_a2a(ra, rb):
    r = subprocess.run(["java", "-jar", str(A2A_JAR), str(ra), str(rb)],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        try: return float(line.strip())
        except: pass
    return None


def run_cvg(ra, rb):
    r = subprocess.run(["java", "-jar", str(CVG_JAR), str(ra), str(rb)],
                       capture_output=True, text=True)
    for line in r.stdout.splitlines():
        for token in line.split():
            try: return float(token)
            except: pass
    return None


def main():
    arc_files = {k: ARC_DIR / f"tika_arc_alpha0.5_k{k}.rsf" for k in K_VALUES}

    other_files = {}
    for k in K_VALUES:
        other_files[f"WCA UEMNM {k}"]  = OTHER_DIR / f"WCA_UEMNM_{k}.rsf"
        other_files[f"Limbo IL {k}"]   = OTHER_DIR / f"Limbo_IL_{k}.rsf"
    other_files["ACDC default"] = OTHER_DIR / "ACDC_default.rsf"

    rows = []
    for ka, ra in arc_files.items():
        if not ra.exists():
            print(f"  MISSING: {ra.name}"); continue
        for label, rb in other_files.items():
            if not rb.exists():
                print(f"  MISSING: {rb.name}"); continue
            score = run_a2a(ra, rb)
            if score is None: continue
            cvg = run_cvg(ra, rb)
            rows.append((f"ARC k={ka}", label, score, cvg))
            print(f"  ARC k={ka:<4} vs {label:<20} A2a={score:.2f} CVG={cvg}")

    rows.sort(key=lambda r: r[2], reverse=True)

    table_path = BASE / "arc_comparison.txt"
    hdr = f"{'ARC':<14} {'Other':<22} {'A2A':>7} {'CVG':>6}"
    with open(table_path, "w") as f:
        f.write(hdr + "\n")
        f.write("-" * len(hdr) + "\n")
        for arc_label, other_label, score, cvg in rows:
            f.write(f"{arc_label:<14} {other_label:<22} {score:>7.2f} {cvg:>6.2f}\n")

    print(f"\nSaved to {table_path}\n")
    with open(table_path) as f:
        print(f.read())


if __name__ == "__main__":
    main()
