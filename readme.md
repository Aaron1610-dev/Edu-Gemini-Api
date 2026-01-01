## 1) Tạo môi trường ảo (venv)

Tại thư mục project:

```bash
python -m venv .env
```

Kích hoạt venv:

- macOS / Linux:
```bash
source .env/bin/activate
```

- Windows (PowerShell):
```powershell
.env\Scripts\Activate.ps1
```

---

## 2) Cài dependencies

```bash
pip install -U pip
pip install python-dotenv pypdf google-genai
```


## 3) Tạo file `config.env` để xoay vòng API keys

Tạo file `config.env` ở **cùng cấp với `main.py`**, nội dung:

```env
GEMINI_API_KEYS=key1,key2,key3,key4,key5,key6,key7,key8,key9,key10,key11,key12,key13,key14,key15,key16,key17,key18,key19,key20
```

Lưu ý:
- Các key cách nhau bởi dấu phẩy `,`
- Không cần dấu ngoặc kép
- Không để khoảng trắng thừa trước/sau mỗi key

---

## 4) Chỉ định file PDF cần xử lý trong `main.py`

Mở `main.py` và chỉnh đường dẫn file PDF:

```python
pdf_path = "test1.pdf"
```

Bạn có thể:
- Đặt PDF cùng thư mục với `main.py`, hoặc
- Ghi đường dẫn tuyệt đối/đường dẫn tương đối tới PDF.

---

## 5) Chạy chương trình

```bash
python main.py
```

Nếu thư mục `Output/` chưa tồn tại, chương trình sẽ tự tạo. Kết quả sau khi chạy xong:

```
Output/
  <pdf_name>/
    <pdf_name>.json
    Topic/
      <pdf_name>_topic_01.pdf
      ...
    Lesson/
      <pdf_name>_lesson_01.pdf
      ...
```

---