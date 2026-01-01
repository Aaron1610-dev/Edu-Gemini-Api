# sgk_extract/gemini_runner.py
import json
from google import genai
from google.genai import types
from google.genai.errors import ClientError


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
            return json.loads(raw)

        except ClientError as e:
            last_err = e
            print(f"[KeyRotation] Key#{key_idx+1}/{n} error: {getattr(e, 'status_code', '')} {str(e)[:120]}")

            if _should_rotate(e):
                continue  # thử key kế tiếp

            # lỗi kiểu PDF hỏng "The document has no pages." => đổi key không giúp => dừng
            raise

        except json.JSONDecodeError as e:
            raise RuntimeError("Gemini trả về không phải JSON hợp lệ.") from e

    raise RuntimeError("Tất cả keys đều đang lỗi quota/rate/invalid.") from last_err
