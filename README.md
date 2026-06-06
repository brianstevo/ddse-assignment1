# DDSE Assignment 1 — Apache Tika Architectural Recovery

**Subject System:** Apache Tika (commit `36211dda7`)
**Scope:** `org.apache.tika.detect` + `org.apache.tika.parser` + `org.apache.tika.mime` — 157 classes

---

## Folder Structure

### week1 — Structural Clustering (WCA, Limbo, ACDC)
Runs three clustering algorithms on the Tika dependency RSF using the ARCADE tool suite.

| Folder | Contents |
|--------|----------|
| `rsf/` | Input RSF files: `tika_detect_parser.rsf` (filtered dependencies), `tika_master.rsf` (full system) |
| `wca/` | WCA UEMNM output RSF files for k = 5, 10, 20, 30, 40, 50 |
| `limbo/` | Limbo IL output RSF files for k = 5, 10, 20, 30, 40, 50 |
| `acdc/` | ACDC default output RSF (4 clusters, pattern-driven) |
| `steps.txt` | Commands and stopthreshold explanation |
| `effort_table.txt` | Time tracking |

**Key note:** WCA produces 1 giant cluster + singletons for k < 50 on this dataset. Limbo k=10 selected as best for Week 4 (highest CVG@30 vs ARC). ACDC auto-detects 4 clusters.

---

### week2 — Comparative Evaluation (A2a + CVG)
Compares WCA, Limbo, and ACDC clusterings using ARCADE metrics.

| File | Contents |
|------|----------|
| `a2a_cvg_comparison.py` | Runs all clusterings and computes A2a + strict CVG for all cross-algorithm pairs |
| `a2a_cvg_comparison.txt` | Full comparison table (one direction per pair, sorted by A2a descending) |
| `wca_vs_limbo.py` | Compares WCA UEMNM vs Limbo IL across all k values |
| `wca_vs_limbo.txt` | WCA vs Limbo comparison table |

**Metrics:**
- **A2a** — Architecture-to-Architecture similarity (0–100)
- **CVG** — Strict containment coverage (cluster A fully contained in cluster B)

---

### week3 — Semantic Clustering (ARC)
Augments structural dependencies with semantic embeddings using `nomic-ai/nomic-embed-code` (run on Google Colab).

| Folder/File | Contents |
|-------------|----------|
| `input/` | `tika_detect_parser.rsf` + `tika_sources.zip` (uploaded to Colab) |
| `ddseweek3file.ipynb` | ARC clustering notebook (ALPHA=0.5, k=5–50) |
| `collab_output/rsf/` | ARC RSF files: `tika_arc_alpha0.5_k5.rsf` … `tika_arc_alpha0.5_k50.rsf` |
| `collab_output/plots/` | Cluster size bar charts, similarity heatmap, dendrogram |
| `arc_comparison.py` | Compares ARC (all k) vs WCA, Limbo, ACDC — computes A2a + CVG |
| `arc_comparison.txt` | ARC comparison results sorted by A2a descending |

**ALPHA=0.5** means 50% structural similarity + 50% semantic similarity.

---

### week4 — LLM-Based Architectural Recovery (HCAG)
Hierarchical summarization of clusters using `Qwen/Qwen2.5-72B-Instruct` on HPC Noctua2 (2× A100 GPUs).

| Folder/File | Contents |
|-------------|----------|
| `input/` | `arc_k5.rsf`, `limbo_k10.rsf`, `ACDC_default.rsf` — input clusters for LLM |
| `hcag_final.py` | HCAG pipeline: leaf pass (file summaries) + branch pass (cluster title + description) |
| `hcag_final.sh` | Slurm job script (GPU partition, 8h, 2× A100) |

**Output (downloaded after job 33127677):**
- `arc_clusters.csv` — ARC k=5 cluster descriptions
- `limbo_clusters.csv` — Limbo k=10 cluster descriptions
- `acdc_clusters.csv` — ACDC cluster descriptions
- `hcag_final_results.json` — Raw JSON with all cluster data
- `hcag_33127677.log` — Job execution log

**Prompting:** Zero-shot with explicit instructions for Components & Interactions, Quality Attributes, Technology Used, and a 150-word limit.

---

## Tools Used

| Tool | Purpose |
|------|---------|
| ARCADE JavaParser | Extract dependency RSF from compiled JAR |
| ARCADE Clusterer | WCA and Limbo clustering |
| ARCADE ACDC | Pattern-based structural clustering |
| ARCADE A2a | Architecture-to-Architecture similarity |
| ARCADE Cvg | Strict containment coverage |
| nomic-ai/nomic-embed-code | Semantic embeddings for ARC (Google Colab) |
| Qwen/Qwen2.5-72B-Instruct | LLM for hierarchical summarization (HPC Noctua2) |
