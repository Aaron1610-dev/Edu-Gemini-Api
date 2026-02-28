# sgk_extract/gemini_runner.py
import json
import re

from google import genai
from google.genai import types
from google.genai.errors import ClientError


def _parse_json_loose(text: str) -> dict:

    """
    Gemini đôi khi trả:
    - JSON trong ```json ... ```
    - hoặc có thêm chữ trước/sau
    Hàm này cố gắng lấy khối JSON lớn nhất hợp lý để parse.
    """
    clean = (text or "").strip()

    # 1) Ưu tiên JSON trong ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return json.loads(m.group(1))

    # 2) Fallback: lấy từ dấu { đầu tiên đến dấu } cuối cùng
    first = clean.find("{")
    last = clean.rfind("}")
    if first != -1 and last != -1 and last > first:
        return json.loads(clean[first:last + 1])

    # 3) Không thấy JSON
    raise json.JSONDecodeError("No JSON object found", clean, 0)


def _should_rotate(err: ClientError) -> bool:
    status = getattr(err, "status_code", None)
    msg = str(err).lower()

    # hay gặp khi hết quota / rate limit / key lỗi
    if status in (401, 403, 429):
        return True

    keywords = ["resource_exhausted", "quota", "rate", "limit", "exceeded", "too many requests"]
    return any(k in msg for k in keywords)


def extract_structure_from_pdf(
    key_manager,
    pdf_path: str,
    prompt: str,
    model: str = "gemini-2.5-flash",
) -> dict:
    """
    Rotate keys: thử key1 -> fail quota/rate -> thử key2 -> ...
    Thành công thì return dict.
    """
    keys = key_manager.keys
    n = len(keys)
    start_idx = key_manager.get_start_index_and_advance()

    config = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="application/json",
    )

    last_err = None

    for step in range(n):
        key_idx = (start_idx + step) % n
        api_key = keys[key_idx]
        raw = ""
        try:
            client = genai.Client(api_key=api_key)

            # Đổi key => upload lại
            uploaded = client.files.upload(file=pdf_path)

            resp = client.models.generate_content(
                model=model,
                contents=[prompt, uploaded],
                config=config,
            )

            raw = (resp.text or "").strip()
            return _parse_json_loose(raw)

        except ClientError as e:
            last_err = e
            print(f"[KeyRotation] Key#{key_idx+1}/{n} error: {getattr(e, 'status_code', '')} {str(e)[:120]}")

            if _should_rotate(e):
                continue  # thử key kế tiếp

            # lỗi kiểu PDF hỏng "The document has no pages." => đổi key không giúp => dừng
            raise

        except json.JSONDecodeError as e:
            snippet = (raw[:500] + "..." if len(raw) > 500 else raw)
            raise RuntimeError(f"Gemini trả về không phải JSON hợp lệ. Snippet:\n{snippet}") from e

    raise RuntimeError("Tất cả keys đều đang lỗi quota/rate/invalid.") from last_err
