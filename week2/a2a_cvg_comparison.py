#!/usr/bin/env python3
"""
Run all clustering configurations, compute A2a + CVG (strict + Jaccard thresholds),
output final_table.txt sorted by A2a descending.
"""

import subprocess, shutil
from pathlib import Path
from collections import defaultdict

BASE      = Path(__file__).parent
DSSE      = Path("/home/brian/Documents/master_cs/dsse")
ARCADE    = DSSE / "assignment1/arcade_tools/arcade_tools"
ARCADE_W2 = DSSE / "assignment1/Arcade_Tools_W2"
CLUSTERER = ARCADE / "arcade_core_clusterer.jar"
ACDC_JAR  = ARCADE / "arcade_core-ACDC.jar"
A2A_JAR   = ARCADE_W2 / "arcade_core_A2a.jar"
CVG_JAR   = ARCADE_W2 / "arcade_core_Cvg.jar"
RSF_SRC   = DSSE / "assignment1Rework/output/rsf/tika_filtered.rsf"

TMP       = Path("/tmp/tika_final")
OUT       = DSSE / "Assignment1FinalWeek/output"
K_VALUES  = [5, 10, 20, 30, 40, 50]
PROJNAME  = "tika"
PROJVER   = "36211dda7"
PREFIX    = "org.apache.tika"


def setup():
    TMP.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(RSF_SRC, TMP / "tika_filtered.rsf")
    print("RSF copied.")


def run_clusterer(algo, measure, k):
    projpath = TMP / f"{algo.lower()}_{measure.lower()}_{k}"
    projpath.mkdir(parents=True, exist_ok=True)
    cmd = [
        "java", "-Xmx4096m", "-jar", str(CLUSTERER),
        f"algo={algo}", "language=java",
        f"deps={TMP}/tika_filtered.rsf",
        f"measure={measure}",
        f"projname={PROJNAME}", f"projversion={PROJVER}",
        f"projpath={projpath}",
        "stop=preselected", f"stopthreshold={k}",
        "serial=archsize", f"serialthreshold={k}",
        f"packageprefix={PREFIX}",
    ]
    subprocess.run(cmd, capture_output=True)
    rsfs = list(TMP.rglob(f"*_{measure}_{k}_clusters.rsf"))
    if not rsfs:
        print(f"  WARNING: No output for {algo} {measure} k={k}")
        return None
    dest = OUT / f"{algo}_{measure}_{k}.rsf"
    shutil.copy(rsfs[0], dest)
    print(f"  {dest.name}")
    return dest


def run_acdc():
    projpath = TMP / "acdc_default"
    projpath.mkdir(parents=True, exist_ok=True)
    src = projpath / "tika_acdc.rsf"
    subprocess.run([
        "java", "-Xmx4096m", "-jar", str(ACDC_JAR),
        str(TMP / "tika_filtered.rsf"), str(src)
    ], capture_output=True)
    if not src.exists():
        print("  WARNING: ACDC produced no output")
        return None
    dest = OUT / "ACDC_default.rsf"
    shutil.copy(src, dest)
    print(f"  {dest.name}")
    return dest


def parse_rsf(path):
    clusters = defaultdict(set)
    with open(path) as f:
        for line in f:
            p = line.strip().split()
            if len(p) == 3 and p[0] == "contain":
                clusters[p[1]].add(p[2])
    return clusters


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


def cvg_jaccard(ra, rb, threshold):
    ca, cb = parse_rsf(ra), parse_rsf(rb)
    if not ca: return 0.0
    covered = sum(
        1 for ca_c in ca.values()
        if max((len(ca_c & cb_c) / len(ca_c | cb_c)
                for cb_c in cb.values()), default=0) >= threshold / 100
    )
    return round(covered / len(ca) * 100, 2)


def cluster_stats(path):
    c = parse_rsf(path)
    sizes = [len(v) for v in c.values()]
    if not sizes: return 0, 0, 0, 0
    return len(sizes), sum(sizes), max(sizes), sum(1 for s in sizes if s == 1)


def main():
    setup()

    rsf_files = {}

    print("\n=== WCA UEMNM ===")
    for k in K_VALUES:
        rsf = run_clusterer("WCA", "UEMNM", k)
        if rsf: rsf_files[f"WCA UEMNM {k}"] = rsf

    print("\n=== Limbo IL ===")
    for k in K_VALUES:
        rsf = run_clusterer("Limbo", "IL", k)
        if rsf: rsf_files[f"Limbo IL {k}"] = rsf

    print("\n=== ACDC ===")
    rsf = run_acdc()
    if rsf: rsf_files["ACDC default"] = rsf

    # Print cluster stats
    print("\n=== Cluster Stats ===")
    print(f"{'Algorithm':<20} {'Clusters':>8} {'Classes':>8} {'Max':>6} {'Singletons':>10}")
    print("-" * 56)
    for label, path in sorted(rsf_files.items()):
        nc, tot, mx, sg = cluster_stats(path)
        print(f"{label:<20} {nc:>8} {tot:>8} {mx:>6} {sg:>10}")

    # Compute metrics for all cross-algorithm pairs (one direction per pair)
    print("\n=== Computing metrics ===")
    rows = []
    seen = set()
    keys = list(rsf_files.keys())

    for ka in keys:
        for kb in keys:
            if ka == kb: continue
            if (kb, ka) in seen: continue
            a_algo = ka.split()[0]
            b_algo = kb.split()[0]
            if a_algo == b_algo: continue

            ra, rb = rsf_files[ka], rsf_files[kb]
            score = run_a2a(ra, rb)
            if score is None: continue
            cvg = run_cvg_strict(ra, rb)
            rows.append((ka, kb, score, cvg))
            seen.add((ka, kb))
            print(f"  {ka:<20} vs {kb:<20} A2a={score:.2f} CVG={cvg}")

    rows.sort(key=lambda r: r[2], reverse=True)

    # Write table
    table_path = BASE / "a2a_cvg_comparison.txt"
    hdr = f"{'A':<22} {'B':<22} {'A2A':>7} {'CVG':>6}"
    with open(table_path, "w") as f:
        f.write(hdr + "\n")
        f.write("-" * len(hdr) + "\n")
        for ka, kb, score, cvg in rows:
            f.write(f"{ka:<22} {kb:<22} {score:>7.2f} {cvg:>6.2f}\n")

    print(f"\nSaved to {table_path}")
    print()
    with open(table_path) as f:
        print(f.read())


if __name__ == "__main__":
    main()
