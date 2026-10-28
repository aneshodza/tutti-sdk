import base64
import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.parse import unquote_to_bytes

import httpx

from .errors import TuttiAuthError
from .svg import render_svg_to_png


@dataclass(frozen=True)
class CaptchaChallenge:
    data: bytes  # decoded image bytes
    content_type: str  # e.g. "image/svg+xml"
    data_uri: str  # original data: URI as found on the login page


class CaptchaProvider(Protocol):
    """Strategy for turning a captcha image into its solution text."""

    def solve(self, challenge: CaptchaChallenge) -> str: ...


def parse_data_uri(data_uri: str) -> CaptchaChallenge:
    """Parse a ``data:<mime>;base64,<payload>`` URI into a challenge."""
    m = re.match(r"^data:([^;,]+)(;base64)?,(.*)$", data_uri, re.DOTALL)
    if not m:
        raise ValueError("Unrecognized captcha data URI")
    content_type, is_base64, payload = m.groups()
    data = base64.b64decode(payload) if is_base64 else unquote_to_bytes(payload)
    return CaptchaChallenge(data=data, content_type=content_type, data_uri=data_uri)


def _ext_for(content_type: str) -> str:
    if "svg" in content_type:
        return "svg"
    if "png" in content_type:
        return "png"
    if "jpeg" in content_type or "jpg" in content_type:
        return "jpg"
    return "img"


class ManualCaptchaProvider:
    """Saves the captcha image for the user and waits for them to type the
    solution. Pass ``save``/``prompt`` to replace the default disk + stdin I/O."""

    def __init__(
        self,
        save: Callable[[CaptchaChallenge], None] | None = None,
        prompt: Callable[[CaptchaChallenge], str] | None = None,
        save_path: str | None = None,
    ) -> None:
        self._save = save or self._default_save
        self._prompt = prompt or self._default_prompt
        self._save_path = save_path

    def solve(self, challenge: CaptchaChallenge) -> str:
        self._save(challenge)
        return self._prompt(challenge).strip()

    def _default_save(self, challenge: CaptchaChallenge) -> None:
        path = self._save_path or f"tutti-captcha.{_ext_for(challenge.content_type)}"
        Path(path).write_bytes(challenge.data)
        print(f"[captcha] saved to {path} — open it and read the text.")

    def _default_prompt(self, challenge: CaptchaChallenge) -> str:
        return input("[captcha] enter the text shown in the image: ")


_DEFAULT_PROMPT = "Extract the 6 characters in this image, only a-zA-Z0-9 allowed"


class LLMCaptchaProvider:
    """Solves captchas with Google's Generative Language API (Gemini) via vision:
    the image is sent as inline_data and the model returns the characters.

    Gemini rejects ``image/svg+xml`` and the tutti captcha is an SVG, so SVGs are
    rasterized with the built-in renderer unless ``rasterize`` is supplied.
    """

    def __init__(
        self,
        api_key: str | None = None,  # default: $GEMINI_API_KEY
        model: str = "gemini-3.1-flash-lite",
        prompt: str = _DEFAULT_PROMPT,
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        mime_type: str | None = None,  # override the mime type sent to the model
        max_retries: int = 4,  # retries on 429/500/503, exponential backoff
        rasterize: Callable[[CaptchaChallenge], tuple[bytes, str]] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._prompt = prompt
        self._base_url = base_url
        self._mime_type = mime_type
        self._max_retries = max_retries
        self._rasterize = rasterize
        self._http = http_client

    def solve(self, challenge: CaptchaChallenge) -> str:
        api_key = self._api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise TuttiAuthError(
                "LLMCaptchaProvider: no API key (set GEMINI_API_KEY or pass api_key)"
            )

        raster = self._rasterize(challenge) if self._rasterize else None
        if raster is None and re.search(r"svg|xml", challenge.content_type, re.IGNORECASE):
            raster = (render_svg_to_png(challenge.data.decode("utf-8")), "image/png")
        mime_type = self._mime_type or (raster[1] if raster else challenge.content_type)
        data = base64.b64encode(raster[0] if raster else challenge.data).decode("ascii")

        url = f"{self._base_url}/models/{self._model}:generateContent"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": data}},
                        {"text": self._prompt},
                    ]
                }
            ]
        }
        headers = {"x-goog-api-key": api_key}

        client = self._http or httpx.Client(timeout=60)
        try:
            res = client.post(url, json=payload, headers=headers)
            attempt = 0
            while res.is_error:
                transient = res.status_code in (429, 500, 503)
                if not transient or attempt >= self._max_retries:
                    raise TuttiAuthError(
                        f"LLM captcha request failed: HTTP {res.status_code} {res.text}"
                    )
                time.sleep(0.8 * 2**attempt)
                attempt += 1
                res = client.post(url, json=payload, headers=headers)
            body = res.json()
        finally:
            if self._http is None:
                client.close()

        parts = ((body.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
        m = re.search(r"[A-Za-z0-9]{6}", text)
        solution = m.group(0) if m else re.sub(r"[^A-Za-z0-9]", "", text)[:6]
        if not solution:
            raise TuttiAuthError(f"LLM returned no usable captcha solution: {text[:100]}")
        return solution
