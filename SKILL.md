---
name: markpdf-python
description: Best practices for the markpdf Python SDK (PDF/DOCX/etc to Markdown conversion). Use when writing code that imports `markpdf` — method choice, error handling/retry, streaming, RAG with pdf_index, API key safety.
---

# Best practices — markpdf (Python)

## Choosing the right method

| Situation | Method |
|---|---|
| Bytes already in memory (FastAPI/Flask upload, prior download) | `convert_bytes(data, filename)` — avoids extra I/O and multipart overhead |
| File on disk | `convert_file(path)` |
| Document already in storage (S3/R2/Supabase/self-hosted) | `convert_from_url(url)` — lets the server download it, no raw-upload limit |
| Large document, want progressive feedback | `convert_stream(...)` |
| Need to navigate a large PDF without converting it whole (RAG/agents) | `pdf_index(url)` first, then `convert_from_url(url, pages="47-58")` with only the relevant pages |

## Error handling and retry

- Catch **specific** exceptions, not generic `MarkpdfError`, when behavior should differ:
  ```python
  from markpdf import RateLimitError, ConversionError, MarkpdfError

  try:
      result = client.convert_file(path)
  except RateLimitError:
      time.sleep(2 ** attempt)  # exponential backoff, retry
  except ConversionError:
      result = client.convert_file(path, mode="balanced")  # retry with another mode
  except MarkpdfError as e:
      logger.error("conversion failed: %s (status=%s)", e, e.status_code)
      raise
  ```
- Only retry `RateLimitError` (429) and 5xx errors. Never retry 400/401/403/413/415/422 without fixing the request first — a retry won't change the outcome.
- If a PDF fails at `mode="fast"`, bump to `mode="balanced"` before giving up. For scanned docs, add `ocr=True`.

## Performance

- `mode="fast"` is the right default for the general case (agents, automated pipelines). Only go to `balanced`/`quality` if `fast` output is poor.
- `slim=True` cuts tokens if you're feeding the Markdown to an LLM (strips repeated headers/footers).
- Use `AsyncMarkpdfClient` when converting many documents concurrently (`asyncio.gather`) — the sync client blocks the thread per request.

## Security

- Never hardcode `api_key=`. Let the client read `MARKPDF_API_KEY` from the environment.
- Don't log the `x-api-key` header or a full pre-signed URL (`output_url`/`url`) — they can carry temporary credentials in the query string.

## Resources

- Full API contract: https://docs.markpdf.tech/docs/sdks/python
- See `AGENTS.md` in this folder for the exact SDK surface.
