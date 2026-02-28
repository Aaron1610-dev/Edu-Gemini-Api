# scripts/kaggle_config.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

def find_project_root() -> Path:
    # scripts/ nằm ngay dưới project root
    return Path(__file__).resolve().parents[1]

PROJECT_ROOT = find_project_root()

# ==== Kaggle IDs ====
KERNEL_REF  = os.getenv("KAGGLE_KERNEL_REF", "dat261303/debug-cutlines-auto")
DATASET_ID  = os.getenv("KAGGLE_DATASET_ID", "dat261303/kaggle-pack")

# ==== In-project paths ====
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

KERNEL_DIR  = SCRIPTS_DIR / "kaggle_kernel_cutlines"
PACK_DIR    = PROJECT_ROOT / "kaggle_pack"  # bạn đang dùng sẵn

# kernel slug để đặt folder output gọn
KERNEL_SLUG = KERNEL_REF.split("/", 1)[1] if "/" in KERNEL_REF else KERNEL_REF

KAGGLE_OUT_ROOT = PROJECT_ROOT / "Output" / "_kaggle_outputs" / KERNEL_SLUG
DL_DIR          = KAGGLE_OUT_ROOT / "downloads"

OUTPUT_ROOT     = PROJECT_ROOT / "Output"