from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncIterator

import httpx

from ._base import DEFAULT_BASE_URL, build_convert_params, parse_conversion_response, raise_if_job_failed
from .errors import error_for_status
from .models import Job, JsonResult


class AsyncMarkpdfClient:
    """Async client for the markpdf (Flash PDF to Markdown) API.

    Example:
        >>> from markpdf import AsyncMarkpdfClient
        >>> client = AsyncMarkpdfClient(api_key="...")
        >>> markdown = await client.convert_file("report.pdf", mode="fast")
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 300.0,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.api_key = api_key or os.environ.get("MARKPDF_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Missing API key. Pass api_key= or set the MARKPDF_API_KEY environment variable."
            )
        self.base_url = base_url.rstrip("/")
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._owns_client = http_client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "AsyncMarkpdfClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    def _headers(self, **extra: str) -> dict[str, str]:
        return {"x-api-key": self.api_key, **extra}

    async def _maybe_poll(self, result: str | JsonResult | Job, auto_poll: bool, poll_interval: float | None) -> str | JsonResult | Job:
        if isinstance(result, Job) and auto_poll:
            return await self.wait_for_job(result.job_id, poll_interval=poll_interval or 5.0)
        return result

    # ------------------------------------------------------------------ #
    # Conversion
    # ------------------------------------------------------------------ #

    async def convert_file(
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
        path = Path(path)
        params = build_convert_params(
            input_format=input_format, mode=mode, engine=engine, clean=clean, ocr=ocr,
            image_ocr=image_ocr, hybrid_ocr=hybrid_ocr, response_format=response_format,
            slim=slim, pages=pages, output_url=output_url, output_encoding=output_encoding,
            output_head_url=output_head_url,
        )
        data = path.read_bytes()
        resp = await self._client.post(
            f"{self.base_url}/convert",
            params=params,
            headers=self._headers(),
            files={"file": (path.name, data, "application/octet-stream")},
        )
        result = parse_conversion_response(resp.status_code, resp.headers.get("content-type", ""), resp.text)
        return await self._maybe_poll(result, auto_poll, poll_interval)

    async def convert_bytes(
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
        params = build_convert_params(
            filename=filename, input_format=input_format, mode=mode, engine=engine, clean=clean,
            ocr=ocr, image_ocr=image_ocr, hybrid_ocr=hybrid_ocr, response_format=response_format,
            slim=slim, pages=pages, output_url=output_url, output_encoding=output_encoding,
            output_head_url=output_head_url,
        )
        resp = await self._client.post(
            f"{self.base_url}/convert/raw",
            params=params,
            headers=self._headers(**{"content-type": content_type}),
            content=data,
        )
        result = parse_conversion_response(resp.status_code, resp.headers.get("content-type", ""), resp.text)
        return await self._maybe_poll(result, auto_poll, poll_interval)

    async def convert_from_url(
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
        body: dict[str, Any] = {"url": url}
        if filename:
            body["filename"] = filename
        body.update(build_convert_params(
            input_format=input_format, mode=mode, engine=engine, clean=clean, ocr=ocr,
            image_ocr=image_ocr, hybrid_ocr=hybrid_ocr, response_format=response_format,
            slim=slim, pages=pages, output_url=output_url, output_encoding=output_encoding,
            output_head_url=output_head_url,
        ))
        resp = await self._client.post(
            f"{self.base_url}/convert/from-url",
            headers=self._headers(**{"content-type": "application/json"}),
            json=body,
        )
        result = parse_conversion_response(resp.status_code, resp.headers.get("content-type", ""), resp.text)
        return await self._maybe_poll(result, auto_poll, poll_interval)

    async def convert_stream(
        self,
        path: str | Path | None = None,
        *,
        url: str | None = None,
        filename: str | None = None,
        mode: str = "fast",
        input_format: str = "auto",
        clean: bool = True,
        slim: bool = False,
    ) -> AsyncIterator[str]:
        """Async-iterate Markdown chunks as they arrive.

        Pass exactly one of ``path`` (local file) or ``url`` (remote file).
        """
        if bool(path) == bool(url):
            raise ValueError("Pass exactly one of path= or url=")

        params = {"filename": filename, "input_format": input_format, "mode": mode, "clean": clean, "slim": slim}
        params = {k: v for k, v in params.items() if v is not None}

        if path is not None:
            p = Path(path)
            params.setdefault("filename", p.name)
            data = p.read_bytes()
            async with self._client.stream(
                "POST", f"{self.base_url}/convert/stream", params=params,
                headers=self._headers(), content=data,
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise error_for_status(resp.status_code, body.decode("utf-8", "replace"))
                async for chunk in resp.aiter_text():
                    yield chunk
        else:
            async with self._client.stream(
                "POST", f"{self.base_url}/convert/stream-from-url",
                headers=self._headers(**{"content-type": "application/json"}),
                json={"url": url, **params},
            ) as resp:
                if resp.status_code >= 400:
                    body = await resp.aread()
                    raise error_for_status(resp.status_code, body.decode("utf-8", "replace"))
                async for chunk in resp.aiter_text():
                    yield chunk

    # ------------------------------------------------------------------ #
    # PDF index (for RAG / AI agents)
    # ------------------------------------------------------------------ #

    async def pdf_index(self, url: str, *, filename: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"url": url}
        if filename:
            body["filename"] = filename
        resp = await self._client.post(
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

    async def get_job(self, job_id: str) -> Job:
        resp = await self._client.get(f"{self.base_url}/jobs/{job_id}", headers=self._headers())
        if resp.status_code >= 400:
            raise error_for_status(resp.status_code, resp.json() if resp.text else {})
        return Job.from_dict(resp.json())

    async def wait_for_job(self, job_id: str, *, poll_interval: float = 5.0, timeout: float | None = None) -> Job:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout if timeout else None
        while True:
            job = await self.get_job(job_id)
            if job.is_terminal:
                return raise_if_job_failed(job)
            if deadline and loop.time() >= deadline:
                raise TimeoutError(f"Job {job_id} did not finish within {timeout}s")
            await asyncio.sleep(poll_interval)
