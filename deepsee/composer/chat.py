"""Lossless DeepSeek Chat Completions transport."""

from __future__ import annotations

import copy
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

from deepsee.config.loader import Config, load_config
from deepsee.composer.transport import request_json, stream_json_async


async def chat_async(
    messages: Sequence[Mapping[str, Any]],
    *,
    stream: bool = False,
    config: Config | None = None,
    params: Mapping[str, Any] | None = None,
    model: str | None = None,
) -> dict[str, Any] | AsyncIterator[dict[str, Any]]:
    """Call DeepSeek without flattening messages or response objects."""
    cfg = config if config is not None else load_config()
    payload = copy.deepcopy(dict(params or {}))
    payload.update(
        {
            "model": model or cfg.deepseek.model,
            "messages": copy.deepcopy(list(messages)),
            "stream": stream,
        }
    )
    if stream:
        return stream_json_async(cfg, payload)
    return await request_json(cfg, payload)
