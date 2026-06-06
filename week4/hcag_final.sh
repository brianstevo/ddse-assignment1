#!/bin/bash
#SBATCH --job-name=hcag_final
#SBATCH --output=/scratch/hpc-prf-dssecs/bsaranha/Slurm4/hcag_%j.log
#SBATCH --partition=gpu
#SBATCH --gres=gpu:a100:2
#SBATCH --mem=240G
#SBATCH --time=08:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8

module load lang/Python/3.10.4-GCCcore-11.3.0

SCRATCH=/scratch/hpc-prf-dssecs/bsaranha
SLURM4=$SCRATCH/Slurm4

mkdir -p $SLURM4
mkdir -p $SLURM4/rsf

pip install --quiet transformers accelerate bitsandbytes

export HF_TOKEN=$HF_TOKEN
export HF_HOME=$SCRATCH/huggingface_cache
export HF_HUB_DISABLE_XET=1

echo "Job started: $(date)"
echo "Node: $(hostname)"
nvidia-smi

python -u $SLURM4/hcag_final.py

echo "Job finished: $(date)"
