#!/usr/bin/env python3
"""
Week 4: LLM-Based Architectural Recovery — Hierarchical Summarization (HCAG)
Reference: HCAG by Yusen Wu et al.

Algorithms : ACDC (default), ARC (k=5), Limbo IL (k=10)
Pre-processing: ACDC and Limbo inner-class entries (Foo$Bar) are converted to
                file-level (Foo) and deduplicated before the LLM pipeline runs.

Step 1 (Leaf pass):   For each Java file in a cluster, prompt the LLM to
                      extract a semantic summary (functionality, logic, I/O, deps).
Step 2 (Branch pass): For each cluster, gather all file summaries and prompt
                      the LLM to generate a cluster-level title + description
                      covering components/interactions, quality attributes,
                      and technology used (under 150 words).

Output: JSON (full results) + CSV per algorithm (cluster_ID, files, title, description)

Group 1 LLM (HPC): Qwen/Qwen2.5-72B-Instruct
Subject system   : Apache Tika — detect and parser components
"""

import csv
import json
import os
from pathlib import Path
from collections import defaultdict

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# ── Configuration ─────────────────────────────────────────────────────────────
MODEL_NAME    = "Qwen/Qwen2.5-72B-Instruct"
HF_TOKEN      = os.environ.get("HF_TOKEN", "")

SCRATCH       = Path("/scratch/hpc-prf-dssecs/bsaranha")
os.environ["HF_HOME"] = str(SCRATCH / "huggingface_cache")
os.environ["HF_HUB_DISABLE_XET"] = "1"
RSF_DIR       = SCRATCH / "Slurm4" / "rsf"
TIKA_SRC      = SCRATCH / "tika_repo" / "tika-core" / "src" / "main" / "java"
OUTPUT_DIR    = SCRATCH / "Slurm4"
OUTPUT_JSON   = OUTPUT_DIR / "hcag_final_results.json"

MAX_SRC_CHARS  = 4000
MAX_NEW_TOKENS = 512

# RSF files to process
RSF_FILES = {
    "ACDC":  RSF_DIR / "acdc.rsf",       # 4 clusters (default)
    "ARC":   RSF_DIR / "arc_k5.rsf",     # 5 clusters (alpha=0.5, k=5)
    "Limbo": RSF_DIR / "limbo_k10.rsf",  # 10 clusters (IL, k=10)
}

# Algorithms that need inner-class -> file-level conversion (Foo$Bar -> Foo)
NEEDS_FILE_LEVEL = {"ACDC", "Limbo"}


# ── RSF Parsing ───────────────────────────────────────────────────────────────
def parse_rsf(path: Path, file_level: bool = False) -> dict:
    """
    Returns {cluster_id: [class_name, ...]} sorted for determinism.
    If file_level=True, strips inner-class suffix (Foo$Bar -> Foo) and deduplicates.
    """
    clusters = defaultdict(set)
    with open(path) as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 3 and parts[0] == "contain":
                cls = parts[2].split("$")[0] if file_level else parts[2]
                clusters[parts[1]].add(cls)
    return {k: sorted(v) for k, v in clusters.items()}


# ── Source Code Lookup ────────────────────────────────────────────────────────
def read_source(class_name: str) -> str:
    rel = class_name.replace(".", "/") + ".java"
    p = TIKA_SRC / rel
    if not p.exists():
        return f"// Source not found for {class_name}"
    return p.read_text(encoding="utf-8", errors="ignore")[:MAX_SRC_CHARS]


# ── Model Loading ─────────────────────────────────────────────────────────────
def load_model():
    print(f"Loading model: {MODEL_NAME}", flush=True)
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME, token=HF_TOKEN, trust_remote_code=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        token=HF_TOKEN,
        trust_remote_code=True,
        quantization_config=bnb,
        device_map="auto",
    )
    model.eval()
    print("Model loaded.", flush=True)
    return tokenizer, model


# ── Generation ────────────────────────────────────────────────────────────────
def generate(tokenizer, model, prompt: str) -> str:
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    input_len = inputs["input_ids"].shape[1]
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
        )
    return tokenizer.decode(out[0][input_len:], skip_special_tokens=True).strip()


# ── Prompts ───────────────────────────────────────────────────────────────────
def leaf_prompt(class_name: str, source: str) -> str:
    return f"""You are a software architecture expert analyzing Java source code.

Analyze the following Java class and provide a concise semantic summary covering:
1. Key functionality
2. Core logic
3. Inputs and Outputs
4. Main dependencies (other classes/interfaces it uses)

Class: {class_name}

Source code:
```java
{source}
```

Provide a structured summary in 4-6 sentences. Be concise and technical."""


def branch_prompt(cluster_id: str, algo: str, file_summaries: list) -> str:
    summaries_text = "\n\n".join(
        f"Class: {s['class']}\nSummary: {s['summary']}"
        for s in file_summaries
    )
    return f"""You are a software architecture expert.

Below are semantic summaries of Java classes belonging to a single architectural cluster
identified by the {algo} clustering algorithm (cluster: {cluster_id}).

Your task:
1. Generate a short architectural TITLE (max 5 words) for this cluster.
2. Write a HIGH-LEVEL DESCRIPTION that explicitly covers:
   - Components and Interactions: how the distinct parts of this cluster work together
   - Quality Attributes: the non-functional requirements achieved (e.g., scalability, security, maintainability, extensibility)
   - Technology Used: any frameworks, languages, or tools identified in the code

Keep the description under 150 words.

Class summaries:
{summaries_text}

Respond in this exact format:
TITLE: <title here>
DESCRIPTION: <description here>"""


# ── CSV Output ────────────────────────────────────────────────────────────────
def parse_title_description(raw: str) -> tuple:
    title, description = "", raw.strip()
    for line in raw.splitlines():
        if line.startswith("TITLE:"):
            title = line[len("TITLE:"):].strip()
        elif line.startswith("DESCRIPTION:"):
            description = line[len("DESCRIPTION:"):].strip()
    return title, description


def write_csv(algo: str, clusters_data: dict, output_dir: Path):
    path = output_dir / f"{algo.lower()}_clusters.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["cluster_ID", "files", "title", "description"]
        )
        writer.writeheader()
        for cluster_id, data in clusters_data.items():
            title, description = parse_title_description(data["cluster_description"])
            writer.writerow({
                "cluster_ID": cluster_id,
                "files": "; ".join(data["classes"]),
                "title": title,
                "description": description,
            })
    print(f"  CSV saved: {path}", flush=True)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    import time
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Clone tika if not present
    if not TIKA_SRC.exists():
        print("Cloning Apache Tika...", flush=True)
        import subprocess
        subprocess.run([
            "git", "clone", "--depth=1",
            "https://github.com/apache/tika.git",
            str(SCRATCH / "tika_repo")
        ], check=True)

    tokenizer, model = load_model()

    results = {}
    total_algos = len(RSF_FILES)

    for algo_idx, (algo, rsf_path) in enumerate(RSF_FILES.items(), 1):
        if not rsf_path.exists():
            print(f"[{algo_idx}/{total_algos}] RSF not found, skipping: {rsf_path}", flush=True)
            continue

        file_level = algo in NEEDS_FILE_LEVEL
        clusters = parse_rsf(rsf_path, file_level=file_level)
        total_clusters = len(clusters)
        print(
            f"\n[{algo_idx}/{total_algos}] === Processing {algo} "
            f"({total_clusters} clusters, file_level={file_level}) ===",
            flush=True
        )
        results[algo] = {}

        for c_idx, (cluster_id, classes) in enumerate(clusters.items(), 1):
            t0 = time.time()
            print(
                f"  [{c_idx}/{total_clusters}] Cluster {cluster_id} "
                f"({len(classes)} files) — leaf pass...",
                flush=True
            )

            # ── Step 1: Leaf pass ────────────────────────────────────────────
            file_summaries = []
            for f_idx, cls in enumerate(classes, 1):
                source = read_source(cls)
                prompt = leaf_prompt(cls, source)
                summary = generate(tokenizer, model, prompt)
                file_summaries.append({"class": cls, "summary": summary})
                print(f"    [leaf {f_idx}/{len(classes)}] {cls.split('.')[-1]}", flush=True)

            # ── Step 2: Branch pass ──────────────────────────────────────────
            print(f"  [{c_idx}/{total_clusters}] Cluster {cluster_id} — branch pass...", flush=True)
            prompt = branch_prompt(cluster_id, algo, file_summaries)
            cluster_description = generate(tokenizer, model, prompt)
            elapsed = time.time() - t0
            print(f"  [{c_idx}/{total_clusters}] Done in {elapsed:.0f}s", flush=True)

            results[algo][cluster_id] = {
                "classes": classes,
                "file_summaries": file_summaries,
                "cluster_description": cluster_description,
            }

        # Write CSV immediately after each algorithm finishes
        write_csv(algo, results[algo], OUTPUT_DIR)

    # Write full JSON
    with open(OUTPUT_JSON, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {OUTPUT_JSON}", flush=True)


if __name__ == "__main__":
    main()
