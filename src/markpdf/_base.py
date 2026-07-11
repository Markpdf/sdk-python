from __future__ import annotations

import json as _json
from typing import Any

from .errors import JobFailedError, error_for_status
from .models import Job, JsonResult

DEFAULT_BASE_URL = "https://api.markpdf.tech"


def build_convert_params(
    *,
    filename: str | None = None,
    input_format: str = "auto",
    mode: str = "fast",
    engine: str = "auto",
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
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "input_format": input_format,
        "mode": mode,
        "engine": engine,
        "clean": clean,
        "ocr": ocr,
        "image_ocr": image_ocr,
        "hybrid_ocr": hybrid_ocr,
        "response_format": response_format,
        "slim": slim,
    }
    if filename is not None:
        params["filename"] = filename
    if pages is not None:
        params["pages"] = pages
    if output_url is not None:
        params["output_url"] = output_url
        params["output_encoding"] = output_encoding
        if output_head_url is not None:
            params["output_head_url"] = output_head_url
    return params


def parse_conversion_response(status_code: int, content_type: str, text: str) -> str | JsonResult | Job:
    if status_code == 202:
        return Job.from_dict(_json.loads(text))

    if status_code >= 400:
        detail: Any
        try:
            detail = _json.loads(text)
        except ValueError:
            detail = text
        raise error_for_status(status_code, detail)

    if "application/json" in content_type:
        return JsonResult.from_dict(_json.loads(text))

    return text


def raise_if_job_failed(job: Job) -> Job:
    if job.status == "failed":
        raise JobFailedError(job.error or "Job failed", detail=job.raw)
    return job
