def build_topic_lesson_prompt() -> str:
    return """
Bạn là một chương trình trích xuất cấu trúc từ SGK PDF.

Mục tiêu: Trả về danh sách CHỦ ĐỀ (topic) và danh sách BÀI (lesson) với (start, end) là SỐ TRANG PDF (1-based) để dùng cắt PDF.

Cách làm (bạn tự làm nội bộ, KHÔNG cần trả ra):
1) Đọc trang MỤC LỤC để lấy danh sách:
   - CHỦ ĐỀ và trang IN bắt đầu (start_printed_topic)
   - BÀI và trang IN bắt đầu (start_printed_lesson)
2) Tìm trang bắt đầu CHỦ ĐỀ 1 trong nội dung thật, đọc số trang IN ở chân trang, suy ra độ lệch:
   offset = (pdf_page_thuc_te) - (printed_page)
3) Quy đổi trang IN -> trang PDF:
   start_pdf = start_printed + offset
   end_pdf = (start_printed của mục kế tiếp + offset - 1)
   Mục cuối: end_pdf = trang PDF cuối của file.

YÊU CẦU OUTPUT:
- Chỉ trả về JSON thuần, KHÔNG giải thích, KHÔNG markdown.
- Nếu không chắc về một mục nào thì bỏ mục đó.
- Format đúng như sau:

{
  "list_topic": [
    {"topic_01": {"start": 9, "end": 30}},
    {"topic_02": {"start": 31, "end": 55}}
  ],
  "list_lesson": [
    {"lesson_01": {"start": 9, "end": 13}},
    {"lesson_02": {"start": 14, "end": 18}}
  ]
}

Quy ước:
- start/end là SỐ TRANG PDF (1-based), inclusive.
- start <= end và không vượt quá số trang PDF của file.
- list_lesson: đánh số lesson_01, lesson_02... theo thứ tự xuất hiện trong Mục lục.
"""
