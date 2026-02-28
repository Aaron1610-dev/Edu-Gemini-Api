import json
import subprocess
import shutil
import time
import zipfile
from pathlib import Path

from .connect import get_key_manager
from sgk_extract.chunk_pipeline import run_extract_and_split_chunks_for_book


KERNEL_REF = "dat261303/debug-cutlines-auto"
# thư mục kernel repo local của bạn (đổi nếu khác)
KERNEL_DIR = Path.home() / "kaggle_kernel_cutlines"

# nơi bạn đóng gói dataset để push
PACK_DIR = Path("kaggle_pack")


def run(cmd, cwd=None):
    print(">>>", " ".join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), check=True, cwd=cwd)


def kernel_status(kernel_ref: str) -> str:
    # output dạng:  dat261303/debug-cutlines-auto has status "KernelWorkerStatus.COMPLETE"
    out = subprocess.check_output(["kaggle", "kernels", "status", kernel_ref], text=True)
    return out.strip()


def wait_kernel_complete(kernel_ref: str, poll_sec: int = 20) -> None:
    while True:
        st = kernel_status(kernel_ref)
        print(st)
        if "KernelWorkerStatus.COMPLETE" in st:
            return
        if "KernelWorkerStatus.FAILED" in st or "KernelWorkerStatus.ERROR" in st:
            raise RuntimeError(f"Kernel failed: {st}")
        time.sleep(poll_sec)


def push_kaggle_dataset(book_stem: str):
    # check kaggle cli
    run(["kaggle", "--version"])

    # đóng gói kaggle_pack/
    shutil.rmtree(PACK_DIR, ignore_errors=True)
    (PACK_DIR / "sgk_extract").mkdir(parents=True, exist_ok=True)
    (PACK_DIR / "Output").mkdir(parents=True, exist_ok=True)

    # ✅ copy code bạn muốn Kaggle dùng (optional; kernel của bạn hiện dùng script riêng nên có/không đều ok)
    src_code = Path("sgk_extract/chunk_postprocess.py")
    if src_code.exists():
        shutil.copy2(src_code, PACK_DIR / "sgk_extract/chunk_postprocess.py")

    # copy book output
    src_book = Path("Output") / book_stem
    dst_book = PACK_DIR / "Output" / book_stem
    if not src_book.exists():
        raise FileNotFoundError(f"Không thấy output book: {src_book}")
    shutil.copytree(src_book, dst_book, dirs_exist_ok=True)

    # dataset-metadata.json
    meta = PACK_DIR / "dataset-metadata.json"
    if not meta.exists():
        meta.write_text(
            '{\n'
            '  "title": "kaggle-pack",\n'
            '  "id": "dat261303/kaggle-pack",\n'
            '  "licenses": [{"name": "CC0-1.0"}]\n'
            '}\n',
            encoding="utf-8"
        )

    # push version (zip-mode)
    run([
        "kaggle", "datasets", "version",
        "-p", str(PACK_DIR),
        "-m", f"auto upload after chunk_split: {book_stem}",
        "--dir-mode", "zip",
    ])


def push_and_run_kernel(kernel_dir: Path, kernel_ref: str):
    if not kernel_dir.exists():
        raise FileNotFoundError(f"Không thấy kernel dir: {kernel_dir}")
    # push kernel (thường sẽ tạo version mới và Kaggle sẽ chạy)
    run(["kaggle", "kernels", "push", "-p", str(kernel_dir)])

    # đợi chạy xong
    wait_kernel_complete(kernel_ref)


def download_and_unzip_output(kernel_ref: str, book_stem: str):
    dl_dir = Path.home() / "kaggle_kernel_outputs" / "debug-cutlines-auto"
    dl_dir.mkdir(parents=True, exist_ok=True)

    # download output kernel
    run([
        "kaggle", "kernels", "output", kernel_ref,
        "-p", str(dl_dir),
        "--force"
    ])

    zip_path = dl_dir / f"{book_stem}_postprocessed.zip"
    if not zip_path.exists():
        raise FileNotFoundError(f"Không thấy zip output: {zip_path}")

    # unzip vào Output/ (không xóa Lesson/Topic)
    out_root = Path("Output")
    out_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(out_root)

    print("✅ Unzipped to:", out_root.resolve())
    return zip_path


def run_all(book_stem: str):
    key_manager = get_key_manager("config.env")
    book_dir = Path("Output") / book_stem

    chunk_root = book_dir / "Chunk"
    before_pdfs = len(list(chunk_root.rglob("*.pdf"))) if chunk_root.exists() else 0
    before_json = len(list(chunk_root.rglob("*.json"))) if chunk_root.exists() else 0
    print(f"[BEFORE] chunk_pdfs={before_pdfs} | chunk_json={before_json}")

    summary = run_extract_and_split_chunks_for_book(
        key_manager,
        book_dir,
        model="gemini-2.5-flash",
        resume=True,
    )

    after_pdfs = len(list(chunk_root.rglob("*.pdf"))) if chunk_root.exists() else 0
    after_json = len(list(chunk_root.rglob("*.json"))) if chunk_root.exists() else 0
    print(f"[AFTER ] chunk_pdfs={after_pdfs} | chunk_json={after_json}")
    print("[NEXT ] Now pushing Kaggle dataset...")

    push_kaggle_dataset(book_stem)
    push_and_run_kernel(KERNEL_DIR, KERNEL_REF)
    zip_path = download_and_unzip_output(KERNEL_REF, book_stem)

    print("✅ DONE roundtrip. Output zip:", zip_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    
if __name__ == "__main__":
    run_all("Tin-hoc-10-ket-noi-tri-thuc")