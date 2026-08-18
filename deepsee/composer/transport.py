"""Shared DeepSeek HTTP and SSE transport.

The composer exposes several projections of the same upstream call: one
returns a complete JSON object and another returns text deltas. Transport
details belong here so retries, framing, timeouts, and error mapping have one
implementation.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx

from deepsee.backends.base import retry_request, retry_request_async, stream_request, stream_request_async
from deepsee.config.loader import Config
from deepsee.errors import ComposeError

STREAM_TOTAL_TIMEOUT = 300.0
REQUEST_TIMEOUT = 120.0


def _url(cfg: Config) -> str:
    return f"{cfg.deepseek.base_url.rstrip('/')}/chat/completions"


def _headers(cfg: Config) -> dict[str, str]:
    return {"Authorization": f"Bearer {cfg.deepseek.api_key}"}


def _request_error(cfg: Config, exc: httpx.HTTPStatusError | httpx.HTTPError) -> ComposeError:
    if isinstance(exc, httpx.HTTPStatusError):
        return ComposeError(
            f"DeepSeek API 请求失败: HTTP {exc.response.status_code}",
            model=cfg.deepseek.model,
            status_code=exc.response.status_code,
        )
    return ComposeError(
        f"DeepSeek API 网络错误: {exc.__class__.__name__}",
        model=cfg.deepseek.model,
    )


def _decode_json(cfg: Config, response: httpx.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except (ValueError, TypeError) as exc:
        raise ComposeError("DeepSeek API 响应解析失败", model=cfg.deepseek.model) from exc
    if not isinstance(data, dict):
        raise ComposeError("DeepSeek API 响应解析失败", model=cfg.deepseek.model)
    return data


def request_json_sync(cfg: Config, payload: dict[str, Any]) -> dict[str, Any]:
    """Send one non-streaming request and return its object response."""
    client = httpx.Client(timeout=REQUEST_TIMEOUT, trust_env=False)
    try:
        response = retry_request(
            client,
            "POST",
            _url(cfg),
            retries=cfg.retries,
            json=payload,
            headers=_headers(cfg),
        )
        return _decode_json(cfg, response)
    except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
        raise _request_error(cfg, exc) from exc
    finally:
        client.close()


async def request_json(cfg: Config, payload: dict[str, Any]) -> dict[str, Any]:
    """Async equivalent of :func:`request_json_sync`."""
    client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT, trust_env=False)
    try:
        response = await retry_request_async(
            client,
            "POST",
            _url(cfg),
            retries=cfg.retries,
            json=payload,
            headers=_headers(cfg),
        )
        return _decode_json(cfg, response)
    except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
        raise _request_error(cfg, exc) from exc
    finally:
        await client.aclose()


def _decode_sse_line(cfg: Config, line: str) -> dict[str, Any] | None:
    if not line or not line.startswith("data:"):
        return None
    raw = line[5:].strip()
    if raw == "[DONE]":
        return None
    try:
        value = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ComposeError("DeepSeek 流式响应解析失败", model=cfg.deepseek.model) from exc
    if not isinstance(value, dict):
        raise ComposeError("DeepSeek 流式响应解析失败", model=cfg.deepseek.model)
    return value


def stream_json_sync(
    cfg: Config,
    payload: dict[str, Any],
    *,
    timeout: float = STREAM_TOTAL_TIMEOUT,
) -> Iterator[dict[str, Any]]:
    """Yield complete JSON objects from a DeepSeek SSE response."""
    client = httpx.Client(timeout=REQUEST_TIMEOUT, trust_env=False)
    response: httpx.Response | None = None
    deadline = time.monotonic() + timeout
    try:
        response = stream_request(
            client,
            "POST",
            _url(cfg),
            retries=cfg.retries,
            json=payload,
            headers=_headers(cfg),
        )
        for line in response.iter_lines():
            if time.monotonic() >= deadline:
                raise ComposeError("DeepSeek 流式响应超过总时长限制", model=cfg.deepseek.model)
            if not line or not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if raw == "[DONE]":
                break
            value = _decode_sse_line(cfg, line)
            if value is not None:
                yield value
    except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
        if time.monotonic() >= deadline:
            raise ComposeError("DeepSeek 流式响应超过总时长限制", model=cfg.deepseek.model) from exc
        raise _request_error(cfg, exc) from exc
    finally:
        if response is not None:
            response.close()
        client.close()


async def _bounded_async_iter(lines: AsyncIterator[str], timeout: float) -> AsyncIterator[str]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError("stream total duration exceeded")
        next_item = asyncio.ensure_future(lines.__anext__())
        try:
            done, _ = await asyncio.wait({next_item}, timeout=remaining)
        except asyncio.CancelledError:
            next_item.cancel()
            await asyncio.gather(next_item, return_exceptions=True)
            raise
        if not done:
            next_item.cancel()
            await asyncio.gather(next_item, return_exceptions=True)
            raise asyncio.TimeoutError("stream total duration exceeded")
        try:
            yield next_item.result()
        except StopAsyncIteration:
            return


async def stream_json_async(
    cfg: Config,
    payload: dict[str, Any],
    *,
    timeout: float = STREAM_TOTAL_TIMEOUT,
) -> AsyncIterator[dict[str, Any]]:
    """Async equivalent of :func:`stream_json_sync`."""
    client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT, trust_env=False)
    response: httpx.Response | None = None
    try:
        response = await stream_request_async(
            client,
            "POST",
            _url(cfg),
            retries=cfg.retries,
            json=payload,
            headers=_headers(cfg),
        )
        try:
            async for line in _bounded_async_iter(response.aiter_lines(), timeout):
                if not line or not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if raw == "[DONE]":
                    break
                value = _decode_sse_line(cfg, line)
                if value is not None:
                    yield value
        except asyncio.TimeoutError as exc:
            raise ComposeError("DeepSeek 流式响应超过总时长限制", model=cfg.deepseek.model) from exc
    except (httpx.HTTPStatusError, httpx.HTTPError) as exc:
        raise _request_error(cfg, exc) from exc
    finally:
        if response is not None:
            await response.aclose()
        await client.aclose()
