# AGENTS.md — markpdf (Python)

Guidance for AI agents generating or modifying code that uses this SDK. Read this before writing code that imports `markpdf`.

## What this is

Python client for the markpdf HTTP API (`https://api.markpdf.tech`), which converts PDF/DOCX/XLSX/PPTX/CSV/HTML/TXT to Markdown. This package does **not** convert anything locally — it's an HTTP wrapper. All real logic lives on the server.

## Layout

```
src/markpdf/
  __init__.py       # public exports — ALWAYS import from here, not submodules
  client.py          # MarkpdfClient (sync, httpx.Client)
  async_client.py    # AsyncMarkpdfClient (async, httpx.AsyncClient) — same API, async
  models.py          # Job, JsonResult (dataclasses)
  errors.py          # exception hierarchy + error_for_status()
  _base.py           # shared helpers between sync/async (build_convert_params, parse_conversion_response)
```

## Public surface (don't invent methods that aren't here)

`MarkpdfClient` / `AsyncMarkpdfClient`:
- `convert_file(path, **options)` → `POST /convert` (multipart)
- `convert_bytes(data, filename, **options)` → `POST /convert/raw` (fastest, no multipart overhead)
- `convert_from_url(url, **options)` → `POST /convert/from-url`
- `convert_stream(path=..., url=..., **options)` → generator/async-generator of chunks, `POST /convert/stream[-from-url]`
- `pdf_index(url, filename=None)` → `dict`, `POST /pdf/index`
- `get_job(job_id)` / `wait_for_job(job_id, poll_interval=5.0, timeout=None)` → `Job`

All `convert_*` methods return `str | JsonResult | Job` depending on `response_format` and whether the 202 got auto-polled (`auto_poll=True` by default).

## Rules when generating code with this SDK

1. **Never invent parameters.** Valid ones are in `_base.build_convert_params`: `input_format`, `mode`, `engine`, `clean`, `ocr`, `image_ocr`, `hybrid_ocr`, `response_format`, `slim`, `pages`, `output_url`, `output_encoding`, `output_head_url`. If you need to confirm allowed values (e.g. `mode` accepts `fast|ultra_fast|balanced|quality|auto`), check the public docs, don't assume.
2. **Handle exceptions from `errors.py`**, not generic ones. Each HTTP status code (400/401/403/413/415/422/429/500) has its own class (`BadRequestError`, `AuthenticationError`, etc). All inherit from `MarkpdfError` with `.status_code` and `.detail`.
3. **The result isn't always `str`.** With `response_format="json"` you get `JsonResult`; if the server returns 202 and `auto_poll=False`, you get `Job`. Check the type before treating it as text (`isinstance(result, str)`).
4. **Prefer `convert_bytes` over `convert_file`** when you already have bytes in memory — avoids extra I/O.
5. **Close the client** (`client.close()` / `async with`) or use the context manager pattern (`with MarkpdfClient(...) as client:`).
6. **Never hardcode the API key.** Read `MARKPDF_API_KEY` from the environment (default behavior if you don't pass `api_key=`).

## Commands

```bash
pip install -e ".[dev]"
pytest
```

## Full reference

Public docs: https://docs.markpdf.tech/docs/sdks/python — don't restate what's already documented there; if the agent needs the exact API contract (all parameters, error codes, response shape), consult it before guessing.
