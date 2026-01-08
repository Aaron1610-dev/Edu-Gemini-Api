# chunk_main.py
import json
from pathlib import Path
from connect import get_key_manager
from sgk_extract.chunk_pipeline import run_extract_and_split_chunks_for_book

def main():
    key_manager = get_key_manager("config.env")

    book_stem = "Tin-hoc-10-ket-noi-tri-thuc"
    book_dir = Path("Output") / book_stem

    summary = run_extract_and_split_chunks_for_book(
        key_manager,
        book_dir,
        model="gemini-2.5-flash",
        resume=True,
    )

    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
