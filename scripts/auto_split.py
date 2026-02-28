import sys
import platform
import shutil
import subprocess
from pathlib import Path

from scripts.connect import get_key_manager
from sgk_extract.les_top_pipeline import run_extract_save_split
from sgk_extract.chunk_pipeline import run_extract_and_split_chunks_for_book


def run_kaggle_cli(book_stem: str, *, run_local: bool = True, overwrite: bool = True):
    """
    Chạy scripts.kaggle.cli giống hệt bạn gõ lệnh terminal.
    macOS: dùng caffeinate -dimsu để không sleep.
    """
    base_cmd = [
        sys.executable, "-m", "scripts.kaggle.cli",
        book_stem,
    ]
    if run_local:
        base_cmd.append("--run-local")
    if overwrite:
        base_cmd.append("--overwrite")

    is_macos = (platform.system() == "Darwin")
    caffeinate = shutil.which("caffeinate")

    if is_macos and caffeinate:
        cmd = ["caffeinate", "-dimsu", *base_cmd]
    else:
        cmd = base_cmd

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main():
    key_manager = get_key_manager("config.env")

    # ✅ bạn chỉ cần đổi pdf_path ở đây
    pdf_path = "./Input/Tin-hoc-12-ket-noi-tri-thuc.pdf"
    book_stem = Path(pdf_path).stem
    book_dir = Path("Output") / book_stem

    # 1) book_split (bên trong les_top_pipeline đã xử lý preview 20 trang cho Gemini đọc mục lục)
    data, json_path, split_result = run_extract_save_split(
        key_manager,
        pdf_path,
        model="gemini-2.5-flash-lite",  # nếu muốn, đổi thành "gemini-2.5-flash"
    )
    print(f"\nSaved JSON: {json_path}")
    print(f"Topics created: {len(split_result['topics'])}")
    print(f"Lessons created: {len(split_result['lessons'])}")

    # 2) chunk_split (local)
    summary = run_extract_and_split_chunks_for_book(
        key_manager,
        book_dir,
        model="gemini-2.5-flash-lite",  # nếu muốn, đổi thành "gemini-2.5-flash"
        resume=True,
    )
    print("\n=== CHUNK PIPELINE SUMMARY ===")
    print(summary)

    # 3) kaggle cli (tự truyền book_stem + caffeinate nếu macOS)
    #    Bạn muốn đúng kiểu: caffeinate -dimsu python -m scripts.kaggle.cli <book_stem> --run-local --overwrite
    run_kaggle_cli(book_stem, run_local=True, overwrite=True)

    print("\n✅ DONE: auto_split")


if __name__ == "__main__":
    main()