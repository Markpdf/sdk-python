from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Iterator

import httpx

from ._base import DEFAULT_BASE_URL, build_convert_params, parse_conversion_response, raise_if_job_failed
from .errors import error_for_status
from .models import Job, JsonResult


class MarkpdfClient:
    """Synchronous client for the markpdf (Flash PDF to Markdown) API.

    Example:
        >>> from markpdf import MarkpdfClient
        >>> client = MarkpdfClient(api_key="...")
        >>> markdown = client.convert_file("report.pdf", mode="fast")
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 300.0,
        http_client: httpx.Client | None = None,
    ):
        self.api_key = api_key or os.environ.get("MARKPDF_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Missing API key. Pass api_key= or set the MARKPDF_API_KEY environment variable."
            )
        self.base_url = base_url.rstrip("/")
        self._client = http_client or httpx.Client(timeout=timeout)
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "MarkpdfClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _headers(self, **extra: str) -> dict[str, str]:
        return {"x-api-key": self.api_key, **extra}

    def _maybe_poll(self, result: str | JsonResult | Job, auto_poll: bool, poll_interval: float | None) -> str | JsonResult | Job:
        if isinstance(result, Job) and auto_poll:
            return self.wait_for_job(result.job_id, poll_interval=poll_interval or 5.0)
        return result

    # ------------------------------------------------------------------ #
    # Conversion
    # ------------------------------------------------------------------ #

    def convert_file(
        self,
        path: str | Path,
        *,
        mode: str = "fast",
        engine: str = "auto",
        input_format: str = "auto",
        clean: bool = True,
        ocr: bool = False,
        image_ocr: bool = False,
        hybrid_ocr: bool = False,
        response_format: str = "markdown",
        slim: bool = False,
        pages: str | None = None,
        output_url: str | None = None,
        output_encoding: str = "identity",
        output_head_url: str | None = None,
        auto_poll: bool = True,
        poll_interval: float | None = None,
    ) -> str | JsonResult | Job:
        """Convert a local file via ``POST /convert`` (multipart/form-data)."""
        path = Path(path)
        params = build_convert_params(
            input_format=input_format, mode=mode, engine=engine, clean=clean, ocr=ocr,
            image_ocr=image_ocr, hybrid_ocr=hybrid_ocr, response_format=response_format,
            slim=slim, pages=pages, output_url=output_url, output_encoding=output_encoding,
            output_head_url=output_head_url,
        )
        with path.open("rb") as fh:
            resp = self._client.post(
                f"{self.base_url}/convert",
                params=params,
                headers=self._headers(),
                files={"file": (path.name, fh, "application/octet-stream")},
            )
        result = parse_conversion_response(resp.status_code, resp.headers.get("content-type", ""), resp.text)
        return self._maybe_poll(result, auto_poll, poll_interval)

    def convert_bytes(
        self,
        data: bytes,
        filename: str,
        *,
        content_type: str = "application/octet-stream",
        mode: str = "fast",
        engine: str = "auto",
        input_format: str = "auto",
        clean: bool = True,
        ocr: bool = False,
        image_ocr: bool = False,
        hybrid_ocr: bool = False,
        response_format: str = "markdown",
        slim: bool = False,
        pages: str | None = None,
        output_url: str | None = None,
        output_encoding: str = "identity",
        output_head_url: str | None = None,
        auto_poll: bool = True,
        poll_interval: float | None = None,
    ) -> str | JsonResult | Job:
        """Convert an in-memory document via ``POST /convert/raw`` (fastest path)."""
        params = build_convert_params(
            filename=filename, input_format=input_format, mode=mode, engine=engine, clean=clean,
            ocr=ocr, image_ocr=image_ocr, hybrid_ocr=hybrid_ocr, response_format=response_format,
            slim=slim, pages=pages, output_url=output_url, output_encoding=output_encoding,
            output_head_url=output_head_url,
        )
        resp = self._client.post(
            f"{self.base_url}/convert/raw",
            params=params,
            headers=self._headers(**{"content-type": content_type}),
            content=data,
        )
        result = parse_conversion_response(resp.status_code, resp.headers.get("content-type", ""), resp.text)
        return self._maybe_poll(result, auto_poll, poll_interval)

    def convert_from_url(
        self,
        url: str,
        *,
        filename: str | None = None,
        mode: str = "fast",
        engine: str = "auto",
        input_format: str = "auto",
        clean: bool = True,
        ocr: bool = False,
        image_ocr: bool = False,
        hybrid_ocr: bool = False,
        response_format: str = "markdown",
        slim: bool = False,
        pages: str | None = None,
        output_url: str | None = None,
        output_encoding: str = "identity",
        output_head_url: str | None = None,
        auto_poll: bool = True,
        poll_interval: float | None = None,
    ) -> str | JsonResult | Job:
        """Convert a document fetched by the API from a pre-signed URL via ``POST /convert/from-url``."""
        body: dict[str, Any] = {"url": url}
        if filename:
            body["filename"] = filename
        body.update(build_convert_params(
            input_format=input_format, mode=mode, engine=engine, clean=clean, ocr=ocr,
            image_ocr=image_ocr, hybrid_ocr=hybrid_ocr, response_format=response_format,
            slim=slim, pages=pages, output_url=output_url, output_encoding=output_encoding,
            output_head_url=output_head_url,
        ))
        resp = self._client.post(
            f"{self.base_url}/convert/from-url",
            headers=self._headers(**{"content-type": "application/json"}),
            json=body,
        )
        result = parse_conversion_response(resp.status_code, resp.headers.get("content-type", ""), resp.text)
        return self._maybe_poll(result, auto_poll, poll_interval)

    def convert_stream(
        self,
        path: str | Path | None = None,
        *,
        url: str | None = None,
        filename: str | None = None,
        mode: str = "fast",
        input_format: str = "auto",
        clean: bool = True,
        slim: bool = False,
    ) -> Iterator[str]:
        """Stream a conversion progressively.

        Pass exactly one of ``path`` (local file, uses ``POST /convert/stream``) or
        ``url`` (remote file, uses ``POST /convert/stream-from-url``). Yields Markdown
        chunks as they become available instead of waiting for the full document.
        """
        if bool(path) == bool(url):
            raise ValueError("Pass exactly one of path= or url=")

        params = {"filename": filename, "input_format": input_format, "mode": mode, "clean": clean, "slim": slim}
        params = {k: v for k, v in params.items() if v is not None}

        if path is not None:
            p = Path(path)
            params.setdefault("filename", p.name)
            with p.open("rb") as fh:
                data = fh.read()
            with self._client.stream(
                "POST", f"{self.base_url}/convert/stream", params=params,
                headers=self._headers(), content=data,
            ) as resp:
                if resp.status_code >= 400:
                    body = resp.read()
                    raise error_for_status(resp.status_code, body.decode("utf-8", "replace"))
                yield from resp.iter_text()
        else:
            with self._client.stream(
                "POST", f"{self.base_url}/convert/stream-from-url",
                headers=self._headers(**{"content-type": "application/json"}),
                json={"url": url, **params},
            ) as resp:
                if resp.status_code >= 400:
                    body = resp.read()
                    raise error_for_status(resp.status_code, body.decode("utf-8", "replace"))
                yield from resp.iter_text()

    # ------------------------------------------------------------------ #
    # PDF index (for RAG / AI agents)
    # ------------------------------------------------------------------ #

    def pdf_index(self, url: str, *, filename: str | None = None) -> dict[str, Any]:
        """Fetch a compact structural index of a PDF (``POST /pdf/index``) without converting it."""
        body: dict[str, Any] = {"url": url}
        if filename:
            body["filename"] = filename
        resp = self._client.post(
            f"{self.base_url}/pdf/index",
            headers=self._headers(**{"content-type": "application/json"}),
            json=body,
        )
        if resp.status_code >= 400:
            raise error_for_status(resp.status_code, resp.json() if resp.text else {})
        return resp.json()

    # ------------------------------------------------------------------ #
    # Jobs
    # ------------------------------------------------------------------ #

    def get_job(self, job_id: str) -> Job:
        """Poll the status of an auto-queued conversion (``GET /jobs/{id}``)."""
        resp = self._client.get(f"{self.base_url}/jobs/{job_id}", headers=self._headers())
        if resp.status_code >= 400:
            raise error_for_status(resp.status_code, resp.json() if resp.text else {})
        return Job.from_dict(resp.json())

    def wait_for_job(self, job_id: str, *, poll_interval: float = 5.0, timeout: float | None = None) -> Job:
        """Block until a queued job reaches ``completed`` or ``failed``."""
        deadline = time.monotonic() + timeout if timeout else None
        while True:
            job = self.get_job(job_id)
            if job.is_terminal:
                return raise_if_job_failed(job)
            if deadline and time.monotonic() >= deadline:
                raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")
            time.sleep(poll_interval)
