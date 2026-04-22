# Frontend (Flet)

UI desktop app cho AI Meeting Assistant (giai đoạn đầu gọi trực tiếp `src.*` trong repo, chưa cần FastAPI).

## Cài đặt

Tại repo root:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r frontend\\requirements.txt
pip install -e .
```

## Chạy

```bash
python frontend\\main.py
```

> Lưu ý: Các chức năng Transcribe/Analyze cần biến môi trường (ví dụ `OPENAI_API_KEY`) tương tự Streamlit app.

