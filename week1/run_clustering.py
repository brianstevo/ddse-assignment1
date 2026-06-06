#!/usr/bin/env python3
"""
Run WCA UEMNM, Limbo IL (k=5,10,20,30,40,50) and ACDC clustering on Apache Tika.
Outputs RSF files to week1/wca/, week1/limbo/, week1/acdc/.
"""

import subprocess, shutil
from pathlib import Path

BASE      = Path(__file__).parent
REPO      = BASE.parent
TOOLS     = REPO / "tools"
CLUSTERER = TOOLS / "arcade_core_clusterer.jar"
ACDC_JAR  = TOOLS / "arcade_core-ACDC.jar"
RSF_SRC   = BASE / "rsf/tika_detect_parser.rsf"

TMP       = Path("/tmp/tika_clustering")
WCA_OUT   = BASE / "wca"
LIMBO_OUT = BASE / "limbo"
ACDC_OUT  = BASE / "acdc"
K_VALUES  = [5, 10, 20, 30, 40, 50]
PROJNAME  = "tika"
PROJVER   = "36211dda7"
PREFIX    = "org.apache.tika"


def setup():
    TMP.mkdir(parents=True, exist_ok=True)
    WCA_OUT.mkdir(parents=True, exist_ok=True)
    LIMBO_OUT.mkdir(parents=True, exist_ok=True)
    ACDC_OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(RSF_SRC, TMP / "tika_filtered.rsf")
    print("RSF copied to tmp.")


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
    out_dir = WCA_OUT if algo == "WCA" else LIMBO_OUT
    dest = out_dir / f"{algo}_{measure}_{k}.rsf"
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
    dest = ACDC_OUT / "ACDC_default.rsf"
    shutil.copy(src, dest)
    print(f"  {dest.name}")
    return dest


def main():
    setup()

    print("\n=== WCA UEMNM ===")
    for k in K_VALUES:
        run_clusterer("WCA", "UEMNM", k)

    print("\n=== Limbo IL ===")
    for k in K_VALUES:
        run_clusterer("Limbo", "IL", k)

    print("\n=== ACDC ===")
    run_acdc()

    print("\nDone. RSF files written to week1/wca/, week1/limbo/, week1/acdc/")


if __name__ == "__main__":
    main()
