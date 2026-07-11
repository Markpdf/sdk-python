# markpdf (Python)

Official Python SDK for the [markpdf](https://markpdf.tech) API — convert PDF, DOCX, XLSX, PPTX, CSV, HTML and TXT into clean, LLM-ready Markdown.

markpdf is an HTTP conversion service built for speed: a `fast` mode tuned for AI agents and RAG pipelines, an optional OCR path for scanned documents, and a compact structural index (`pdf_index`) so agents can navigate huge PDFs without paying to convert them whole. This package is a thin, fully-typed wrapper around that HTTP API — it does no conversion locally, so it stays tiny and dependency-light (just [httpx](https://www.python-httpx.org/)).

- **Website:** https://markpdf.tech
- **Full API docs:** https://docs.markpdf.tech
- **PyPI:** `pip install markpdf`

## Table of contents

- [Install](#install)
- [Quickstart](#quickstart)
- [Async usage](#async-usage)
- [Why markpdf](#why-markpdf)
- [Method reference](#method-reference)
- [Conversion options](#conversion-options)
- [Handling large documents](#handling-large-documents)
- [RAG / AI agent pattern](#rag--ai-agent-pattern)
- [Error handling](#error-handling)
- [Auto-queued jobs (202)](#auto-queued-jobs-202)
- [Development](#development)

## Install

```bash
pip install markpdf
```

Requires Python 3.9+.

## Quickstart

```python
from markpdf import MarkpdfClient

client = MarkpdfClient(api_key="YOUR_API_KEY")
markdown = client.convert_file("report.pdf", mode="fast")
print(markdown)
```

By default the client reads `MARKPDF_API_KEY` from the environment, so you can also just do:

```python
client = MarkpdfClient()  # picks up MARKPDF_API_KEY
```

## Async usage

Every method has an async counterpart with the exact same signature, for use in `asyncio`-based apps, FastAPI handlers, or when converting many documents concurrently:

```python
import asyncio
from markpdf import AsyncMarkpdfClient

async def main():
    async with AsyncMarkpdfClient(api_key="YOUR_API_KEY") as client:
        markdown = await client.convert_file("report.pdf")
        print(markdown)

asyncio.run(main())
```

```python
# Convert many documents concurrently
async def convert_many(paths):
    async with AsyncMarkpdfClient() as client:
        return await asyncio.gather(*(client.convert_file(p) for p in paths))
```

## Why markpdf

- **Fast by default.** `mode="fast"` is tuned for throughput — the right choice for agents and pipelines that just need clean text.
- **No wasted tokens.** `slim=True` strips repeated headers/footers before the Markdown reaches your LLM.
- **Cheap navigation of huge PDFs.** `pdf_index()` returns a compact map (sections, headings, per-page stats) in a few KB, so a RAG agent can pick exactly which `pages=` to convert instead of paying for the whole document.
- **Bring your own storage.** `output_url` lets the API upload the converted Markdown straight to your own S3/R2/self-hosted bucket instead of returning it inline — useful for very large outputs.
- **Graceful overload handling.** If the service is at capacity, conversions transparently auto-queue (HTTP 202) and this SDK polls the job for you by default (`auto_poll=True`).

## Method reference

| Method | Endpoint | Use for |
|---|---|---|
| `convert_file(path, **options)` | `POST /convert` | Local file on disk (multipart upload) |
| `convert_bytes(data, filename, **options)` | `POST /convert/raw` | Bytes already in memory — the fastest path, no multipart overhead |
| `convert_from_url(url, **options)` | `POST /convert/from-url` | Document already in storage (S3/R2/Supabase/self-hosted) — the server downloads it |
| `convert_stream(path=..., url=..., **options)` | `POST /convert/stream[-from-url]` | Progressive Markdown output as a generator, for large documents |
| `pdf_index(url, filename=None)` | `POST /pdf/index` | Compact structural map of a PDF, without converting it |
| `get_job(job_id)` / `wait_for_job(job_id, ...)` | `GET /jobs/{id}` | Poll or block on an auto-queued (202) conversion |

Both `MarkpdfClient` (sync, `httpx.Client`) and `AsyncMarkpdfClient` (async, `httpx.AsyncClient`) expose this same set of methods.

## Conversion options

Every `convert_*` method accepts the same keyword options:

```python
client.convert_file(
    "report.pdf",
    mode="fast",              # fast | ultra_fast | balanced | quality | auto
    engine="auto",            # auto | pymupdf | pdf_oxide
    input_format="auto",      # auto | pdf | docx | csv | txt | html | xlsx | pptx | zip
    clean=True,                # strip repeated headers/footers and control chars
    ocr=False,                 # OCR in balanced mode, for scanned PDFs
    image_ocr=False,           # OCR only image regions, not the whole page
    hybrid_ocr=False,          # full-page OCR only on pages with no native text
    response_format="markdown",  # markdown | json
    slim=False,                 # cut tokens further before handing text to an LLM
    pages=None,                  # e.g. "1,3,5-10" — PDF only
    output_url=None,             # pre-signed PUT URL to upload the result to your own storage
    output_encoding="identity",   # identity | gzip | zstd — for output_url uploads
    auto_poll=True,               # transparently wait out a 202 auto-queue
)
```

`response_format="json"` returns a `JsonResult` with the Markdown plus metadata (`engine`, `size_bytes`, `timings`, `token_saved_estimate`) instead of a plain string.

## Handling large documents

For documents too big (or too slow) to hold in memory end-to-end, prefer `convert_from_url` over `convert_file`/`convert_bytes` — the API downloads the document itself and there's no raw-upload size limit:

```python
markdown = client.convert_from_url(
    "https://storage.example.com/signed/report.pdf",
    filename="report.pdf",
    pages="1-50",
)
```

For truly huge PDFs, combine this with the RAG pattern below instead of converting the whole thing.

## RAG / AI agent pattern

```python
from markpdf import MarkpdfClient

client = MarkpdfClient()

# 1. Get a cheap structural map instead of the full document
index = client.pdf_index("https://storage.example.com/signed/report.pdf")

# 2. Decide which pages matter (from index["sections"], your own retrieval, etc.)
relevant_pages = "47-58"

# 3. Convert only those pages
markdown = client.convert_from_url(
    "https://storage.example.com/signed/report.pdf",
    pages=relevant_pages,
)
```

This turns a 500-page PDF into a few KB of index plus a small slice of Markdown, instead of paying to convert (and tokenize) the whole document.

## Error handling

Every non-2xx response raises a typed exception, all inheriting from `MarkpdfError` with `.status_code` and `.detail`:

```python
from markpdf import (
    MarkpdfError, BadRequestError, AuthenticationError, ForbiddenError,
    PayloadTooLargeError, UnsupportedFormatError, UnprocessableEntityError,
    RateLimitError, ConversionError, JobFailedError,
)

try:
    markdown = client.convert_file("report.pdf")
except RateLimitError:
    ...  # back off and retry
except ConversionError:
    markdown = client.convert_file("report.pdf", mode="balanced")  # retry with a stronger mode
except MarkpdfError as e:
    print(f"Conversion failed ({e.status_code}): {e}")
```

| Exception | HTTP status | Meaning |
|---|---|---|
| `BadRequestError` | 400 | Malformed body or URL |
| `AuthenticationError` | 401 | Missing/invalid API key |
| `ForbiddenError` | 403 | Unauthorized access or disallowed URL host |
| `PayloadTooLargeError` | 413 | Document too large / too many pages |
| `UnsupportedFormatError` | 415 | Unsupported format or `Content-Encoding` |
| `UnprocessableEntityError` | 422 | Missing required parameters |
| `RateLimitError` | 429 | Too many requests — retry with backoff |
| `ConversionError` | 500 | Conversion failed — try another `mode` |
| `JobFailedError` | — | A queued job (202) ended with `status=failed` |

## Auto-queued jobs (202)

When the service is at capacity, a conversion returns `202` with a `job_id` instead of failing. By default (`auto_poll=True`), every `convert_*` call already waits out the queue and returns the final result. To handle it manually instead:

```python
result = client.convert_file("report.pdf", auto_poll=False)
if isinstance(result, str):
    print(result)  # completed immediately
else:
    job = client.wait_for_job(result.job_id, poll_interval=5.0, timeout=120.0)
    print(job.body)
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

See `AGENTS.md` and `SKILL.md` in this repo for guidance aimed at AI coding agents working with this SDK.

## License

MIT

## Security and AI-agent checklist

Keep `MARKPDF_API_KEY` in an environment variable or secret manager. Validate file size/type before conversion, authenticate upload endpoints, apply per-user quotas and timeouts, and redact signed URL query strings and document data from logs. Use short-lived HTTPS URLs for remote inputs.

Converted Markdown is untrusted. Escape it before HTML rendering; for RAG and agents, delimit it as data and explicitly prevent document instructions from overriding system/developer policy or authorizing tool calls. Retry only `429`, transient network failures and selected `5xx` responses with bounded exponential backoff and jitter.

Read [`AGENTS.md`](./AGENTS.md), [`SKILL.md`](./SKILL.md), and [`SECURITY.md`](./SECURITY.md) before generating production integration code.

## S3/R2 uploads, downloads and database optimization

For production workloads, upload large files directly from the client to a private S3 or Cloudflare R2 bucket with a short-lived presigned `PUT` URL. Then call this SDK's URL-conversion method so the application server never buffers the full document. Large Markdown results can be written straight back to object storage with the SDK's output URL option where supported.

Recommended flow:

1. Authenticate and authorize the user.
2. Create a database row with a server-generated conversion ID and `uploading` status.
3. Generate a random tenant-scoped object key and a short-lived presigned upload URL.
4. Upload directly to private storage and verify object size/checksum server-side.
5. Reuse a completed conversion only when tenant, input SHA-256 and canonical options hash all match.
6. Convert from a signed input URL; use a signed output URL for large results.
7. Store status and object metadata in the database, while keeping large Markdown bodies in S3/R2.
8. Authorize downloads and return a short-lived signed `GET` URL or a hardened attachment response.
9. Expire temporary objects, abandoned multipart uploads and stale database rows automatically.

Do not use filenames, object URLs or multipart ETags as content identity. Use a verified checksum, normalize every output-affecting conversion option into the cache key, and isolate deduplication by tenant. Keep database indexes focused on tenant history, active jobs and expiry cleanup.

See [`STORAGE.md`](./STORAGE.md) for the full SQL model, partial indexes, idempotent state transitions, cache-key rules, S3/R2 permissions, CORS, multipart uploads, lifecycle policies, secure download headers and AI/RAG protections.
