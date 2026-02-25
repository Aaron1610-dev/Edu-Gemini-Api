from connect import get_key_manager
from sgk_extract.chunk_json_pipeline import extract_chunk_json, save_chunk_json

key_manager = get_key_manager("config.env")

lesson_pdf = "Output/Tin-hoc-11-ket-noi-tri-thuc/Lesson/Tin-hoc-11-ket-noi-tri-thuc_lesson_08.pdf"
data = extract_chunk_json(key_manager, lesson_pdf, model="gemini-2.5-flash")

json_path = save_chunk_json(lesson_pdf, out_dir="Output/Tin-hoc-10-ket-noi-tri-thuc/ChunkJson", data=data)
print("Saved:", json_path)
print(data)