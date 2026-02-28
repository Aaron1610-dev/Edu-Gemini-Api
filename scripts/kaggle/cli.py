# scripts/run_kaggle_cutlines.py
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from scripts.kaggle_config import (
    PROJECT_ROOT, KERNEL_REF, KERNEL_DIR, PACK_DIR,
    DL_DIR, OUTPUT_ROOT,
)
from scripts.kaggle_utils import (
    ensure_kaggle_cli,
    build_kaggle_pack,
    push_dataset_version,
    push_kernel,
    download_kernel_output,
    safe_extract_zip_to_output,
)

def setup_logging(log_file: Path | None, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler()]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book_stem", help="VD: Tin-hoc-10-ket-noi-tri-thuc")
    ap.add_argument("--skip-dataset", action="store_true", help="Không build+version dataset (chỉ push kernel + download)")
    ap.add_argument("--skip-kernel", action="store_true", help="Không push kernel (chỉ download/apply output hiện có)")
    ap.add_argument("--no-apply", action="store_true", help="Chỉ download zip, không giải nén vào Output/")
    ap.add_argument("--overwrite", action="store_true", help="Cho phép ghi đè Output/<book_stem> khi apply")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    log_file = (PROJECT_ROOT / "Output" / "_kaggle_outputs" / KERNEL_REF.split("/",1)[1] / "run.log")
    setup_logging(log_file, args.verbose)
    log = logging.getLogger("run_kaggle_cutlines")

    ensure_kaggle_cli()
    DL_DIR.mkdir(parents=True, exist_ok=True)

    # 1) dataset version (đảm bảo code + Output mới nhất được mount trong kernel)
    if not args.skip_dataset:
        build_kaggle_pack(PACK_DIR, book_stem=args.book_stem, project_root=PROJECT_ROOT)
        push_dataset_version(PACK_DIR, message=f"auto upload: {args.book_stem}", dir_mode="zip")
    else:
        log.info("Skip dataset build/version.")

    # 2) push kernel + wait
    if not args.skip_kernel:
        push_kernel(KERNEL_DIR, KERNEL_REF)
    else:
        log.info("Skip kernel push/wait.")

    # 3) download output
    download_kernel_output(KERNEL_REF, DL_DIR, force=True)

    zip_path = DL_DIR / f"{args.book_stem}_postprocessed.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"Missing kernel zip output: {zip_path}")

    log.info("Downloaded: %s", zip_path)

    # 4) apply zip into Output/
    if not args.no_apply:
        dst = safe_extract_zip_to_output(zip_path, OUTPUT_ROOT, overwrite=args.overwrite)
        log.info("✅ Applied to: %s", dst)
    else:
        log.info("No-apply: kept zip at %s", zip_path)

    log.info("✅ DONE.")

if __name__ == "__main__":
    main()