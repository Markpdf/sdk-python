# markpdf (Python)

Official Python SDK for the [markpdf](https://markpdf.tech) API — convert PDF, DOCX, XLSX, PPTX, CSV, HTML and TXT to clean Markdown.

## Install

```bash
pip install markpdf
```

## Quickstart

```python
from markpdf import MarkpdfClient

client = MarkpdfClient(api_key="YOUR_API_KEY")
markdown = client.convert_file("report.pdf", mode="fast")
print(markdown)
```

## Async

```python
import asyncio
from markpdf import AsyncMarkpdfClient

async def main():
    async with AsyncMarkpdfClient(api_key="YOUR_API_KEY") as client:
        markdown = await client.convert_file("report.pdf")
        print(markdown)

asyncio.run(main())
```

## Features

- Sync (`MarkpdfClient`) and async (`AsyncMarkpdfClient`) clients with the same API.
- `convert_file`, `convert_bytes`, `convert_from_url`, `convert_stream`, `pdf_index`.
- Automatic handling of `202` auto-queued jobs (`auto_poll=True` by default).
- Typed exceptions per HTTP status code (`AuthenticationError`, `RateLimitError`, ...).
- Fully typed, ships `py.typed`.

Full documentation: https://docs.markpdf.tech
