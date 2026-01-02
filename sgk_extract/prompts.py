# sgk_extract/prompts.py
def build_topic_lesson_prompt() -> str:
    return r"""
Bạn là một chương trình trích xuất cấu trúc từ SGK PDF.

MỤC TIÊU:
Trả về:
- list_topic: các CHỦ ĐỀ
- list_lesson: các BÀI
với start/end là SỐ TRANG PDF (1-based), inclusive để cắt PDF.

QUY TẮC NHẬN DIỆN TRONG MỤC LỤC (RẤT QUAN TRỌNG):
1) LESSON (BÀI) CHỈ là các dòng bắt đầu bằng đúng mẫu:
   "Bài <SỐ>."
   Ví dụ hợp lệ: "Bài 31. ...."
   Không hợp lệ và PHẢI BỎ QUA: "Bảng ...", "Phụ lục", "Tài liệu ...", "Đáp án ...", "Mục lục", "Lời nói đầu", ...
   (dù các dòng đó có số trang).

2) TOPIC (CHỦ ĐỀ) CHỈ là các dòng bắt đầu bằng đúng mẫu:
   "Chủ đề <SỐ>."
   Ví dụ: "Chủ đề 7. ...."
   Không dùng các dòng khác làm topic.

3) KẾT THÚC NỘI DUNG (ĐỂ KHÔNG ĂN DƯ PHỤ LỤC):
   - Sau khi tìm ra BÀI CUỐI CÙNG trong Mục lục (dòng "Bài <SỐ>."),
     hãy tìm dòng kế tiếp trong Mục lục mà KHÔNG phải "Bài <SỐ>." và có số trang.
     Dòng đó gọi là "mốc phụ lục/ngoại dung" (ví dụ: "Bảng giải thích...", "Phụ lục"...).
   - Nếu có mốc này:
       printed_end_of_main = (trang IN bắt đầu của mốc này) - 1
     Nếu KHÔNG có mốc này:
       printed_end_of_main = trang IN của trang nội dung cuối cùng (trước phần phụ lục) nếu nhận ra được,
       còn không thì dùng trang PDF cuối của file.

CÁCH LÀM (bạn tự làm nội bộ, KHÔNG cần trả ra):
A) Đọc trang MỤC LỤC để lấy:
   - start_printed_topic cho từng Chủ đề
   - start_printed_lesson cho từng Bài (CHỈ theo mẫu "Bài <SỐ>.")
   - nếu có, lấy start_printed của mốc phụ lục/ngoại dung đầu tiên sau Bài cuối

B) Tính độ lệch trang:
   offset = (pdf_page_thực_tế của trang có số in) - (printed_page in trên chân trang)

C) Quy đổi printed -> pdf:
   start_pdf = start_printed + offset
   end_pdf = (start_printed của mục kế tiếp + offset - 1)

D) Riêng mục CUỐI:
   - BÀI CUỐI:
       end_pdf = printed_end_of_main + offset   (nếu có printed_end_of_main)
       nếu không có printed_end_of_main thì end_pdf = trang PDF cuối của file
   - CHỦ ĐỀ CUỐI:
       end_pdf phải KHÔNG vượt quá end_pdf của BÀI CUỐI (tức là không ăn sang phụ lục).

YÊU CẦU OUTPUT:
- Chỉ trả về JSON thuần, KHÔNG giải thích, KHÔNG markdown.
- Key BẮT BUỘC:
  list_topic: topic_01, topic_02, ...
  list_lesson: lesson_01, lesson_02, ...
- Nếu không chắc mục nào thì bỏ mục đó.
- start/end hợp lệ: 1 <= start <= end <= tổng số trang PDF.

FORMAT:
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
"""

def build_chunk_prompt_start_head(total_pages: int) -> str:
    return f"""
Bạn đang đọc 1 file PDF chỉ chứa DUY NHẤT 1 BÀI (LESSON).

MỤC TIÊU:
Trả về list_chunk là các MỤC CHÍNH của bài theo trang PDF của CHÍNH FILE LESSON này.

CHỈ tạo chunk khi tìm thấy "TIÊU ĐỀ MỤC CHÍNH" hợp lệ.
Nếu không chắc chắn 100% => BỎ QUA (không bịa).

ĐỊNH NGHĨA "TIÊU ĐỀ MỤC CHÍNH" (PHẢI ĐÚNG):
Một tiêu đề mục chính hợp lệ phải thỏa ĐỒNG THỜI:

1) Dòng tiêu đề bắt đầu bằng mẫu: "<số>." (ví dụ "1.", "2.", "3.", ...) ở ĐẦU DÒNG.
2) Phần nội dung sau dấu chấm PHẢI là TIÊU ĐỀ (KHÔNG phải câu):
   - Viết IN HOA TOÀN BỘ (không được có chữ thường).
   - Trông giống một tiêu đề (thường chữ lớn hơn nội dung, có khoảng cách trước/sau).
3) LOẠI TRỪ TUYỆT ĐỐI (KHÔNG BAO GIỜ coi là mục chính), dù có "1." "2.":
   - Dòng thuộc danh sách nhiệm vụ/câu hỏi/bài tập/liệt kê trong đoạn văn.
   - Các dòng kiểu: "1. Em hãy ...", "2. Hãy ...", "1. Nháy ...", "2. Chọn ...", "1. Thực hiện ..."
     (đây là câu hướng dẫn -> thường có chữ thường -> không phải tiêu đề mục chính).
   - Dòng có ngữ khí mệnh lệnh/hướng dẫn (NHÁY, CHỌN, MỞ, THỰC HIỆN, HÃY, EM HÃY...) hoặc là câu dài.
   - Nếu tiêu đề nằm trong khung "NHIỆM VỤ", "CÂU HỎI", "BÀI TẬP", "HƯỚNG DẪN", "BƯỚC" thì KHÔNG lấy.

OUTPUT MỖI CHUNK:
- start: SỐ TRANG PDF (1-based) nơi tiêu đề mục chính xuất hiện lần đầu.
- content_head: true/false
  - true  nếu trên CÙNG trang start, phía TRÊN tiêu đề còn có nội dung thuộc mục trước
          (đoạn văn/hình/bảng/câu hỏi/bài tập/tổng kết...). KHÔNG tính header/footer/số trang.
  - false nếu phía trên chỉ có header/footer/số trang hoặc tiêu đề nằm ngay đầu trang nội dung.

RÀNG BUỘC:
- chunk_01 luôn content_head = false.
- start tăng dần theo thứ tự xuất hiện.
- 1 <= start <= {total_pages}.
- Nếu bài KHÔNG có mục chính hợp lệ theo định nghĩa => trả list_chunk rỗng [].

YÊU CẦU OUTPUT:
- Chỉ JSON thuần, KHÔNG giải thích, KHÔNG markdown.

FORMAT:
{{
  "list_chunk": [
    {{"chunk_01": {{"start": 1, "content_head": false}}}},
    {{"chunk_02": {{ "start": 3, "content_head": true}}}}
  ]
}}
"""
