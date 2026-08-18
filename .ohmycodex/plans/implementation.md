# Issues 5, 6, 7 Implementation

Date: 2026-08-13
Status: complete

## Implemented

- Forwarded and validated `X-DeepSee-Vision-Mode` (`auto`, `ui`, `general`)
  before configuration loading, then passed the selected route to the vision
  composer.
- Mapped configuration failures to sanitized protocol-specific 503 responses,
  validated TOML section types, required JSON booleans for `stream`, and made
  base64 decoding strict and non-empty.
- Centralized minimum DeepSeek SSE chunk validation and fixed Python 3.10 async
  cancellation propagation so malformed streams raise `ComposeError` and
  cancelled streams close their response/client resources.
- Added structured request limits with environment overrides: 100 messages or
  contents, 4 images, 200,000 text characters, default 4,096 output tokens,
  and maximum 8,192 output tokens. Normalized output limits are forwarded to
  DeepSeek rather than only validated at the gateway.
- Replaced request-body chunk accumulation plus `join` with a bounded
  `bytearray`, retaining the existing 32 MiB body and 20 MiB decoded-image
  limits with lower peak copying overhead.
- Added SHA-256-only public/admin API key storage with atomic `0600` writes,
  scope isolation, revocation, and one-time plaintext creation responses.
- Added fail-closed authentication for direct ASGI imports. `/health` remains
  public; protected public/admin paths return 503 until authentication is
  explicitly configured.
- Added public Bearer authentication and separate `X-DeepSee-Admin-Key`
  authentication, plus admin key list/create/revoke endpoints.
- Kept `--no-auth`, restricted at CLI startup to `127.0.0.1`, `::1`, and
  `localhost`.
- Added process-local fixed-window rate limiting and global inference
  concurrency control. Defaults are 60 requests per 60 seconds, 8 concurrent
  requests, and a 2-second queue timeout.
- Kept concurrency leases through the complete response body lifecycle,
  including streaming completion, generator failure, and client cancellation.
- Added CLI first-start and recovery-key behavior plus environment parsing for
  all guard settings.
- Updated README startup, authentication header, recovery key, no-auth, and
  process-local/input/output limiting documentation.
- Made Desktop streaming completion require `[DONE]` or a recognized OpenAI
  finish reason, and added MIME/empty/20 MiB validation before `FileReader` in
  both Composer and Playground.

## Verification

```text
uv run pytest tests/test_server/test_auth.py tests/test_server/test_request_guard.py tests/test_server/test_server_config.py -q
57 passed, 1 warning

uv run pytest tests/test_server/test_app.py -q
78 passed, 1 warning

uv run pytest -q
371 passed, 1 warning

uv build
Successfully built dist/seedeep-0.1.0.tar.gz
Successfully built dist/seedeep-0.1.0-py3-none-any.whl

git diff --check
no output

pnpm test
25 passed

pnpm lint
TypeScript check passed

pnpm build
Vite production build passed

Desktop git diff --check
no output

FastAPI TestClient contract probe
vision_mode=ui, configuration=503, invalid stream=400,
invalid base64=400, overload=503 with Retry-After
```

The warning is the existing Starlette TestClient/httpx2 deprecation warning.

## Residual Risks

- Rate and concurrency state is local to one Python process. Multiple workers
  or instances need shared rate limiting at a reverse proxy or external store.
- Public deployment still requires TLS, reverse-proxy access controls, and
  appropriate network policy.
- Existing unrelated worktree changes were preserved and were included in the
  full test/build verification; no unrelated changes were reverted.
- The request guard and rate windows are intentionally process-local; the
  limits are not shared across multiple workers or instances.
- No paid request was sent to real DeepSeek or vision-provider endpoints; the
  upstream compatibility matrix remains a deployment-time smoke-test item.

# Issue 4 Implementation: Full OpenAI Message History

Date: 2026-08-13
Status: complete

## Implemented

- Added `deepsee.composer.chat.chat_async`, a lossless DeepSeek Chat
  Completions transport that deep-copies full message history and supported
  parameters, preserves non-streaming response objects, and forwards complete
  streaming JSON chunks including tool calls, usage, stable IDs, and finish
  reasons.
- Added a bounded visual-message transformer that replaces only OpenAI
  `image_url` blocks, preserves all other messages and tool fields, combines
  same-message text blocks for the visual question, and wraps analysis in an
  explicitly untrusted `DEEPSEE_VISUAL_CONTEXT` block.
- Enforced four images per request, 12,000 context characters per image,
  32,000 total visual-context characters, existing 20 MiB image limits, and
  process-local 30-minute/128-entry SHA-256-keyed analysis caching.
- Added complete OpenAI request parsing with the approved top-level parameter
  allowlist, strict role/content/stream validation, support for
  `assistant.content: null` plus tool calls, image counting, and preservation
  of unknown object-shaped content blocks for upstream validation.
- Routed `/v1/chat/completions` through the new chat transport. Plain-text and
  visual requests now preserve multi-turn history, tools, tool results, and
  explicit `max_completion_tokens`; normalized output defaults are injected
  only when neither output-token field is supplied.
- Preserved complete DeepSeek non-streaming responses and raw stream deltas.
  The optional `vision_analysis` extension remains gated by
  `X-DeepSee-Include-Vision: 1` and reuses the upstream stream ID.
- Fixed client-disconnect cleanup in the OpenAI SSE wrapper so closing the
  response stream closes the upstream iterator without attempting to emit a
  final `[DONE]` chunk during async-generator shutdown.
- Updated the README to document the OpenAI vision extension as opt-in and
  added an endpoint regression test proving unknown parameters are rejected
  before configuration loading or upstream invocation.
- Kept the existing authentication, CORS, request guard, trace, body-size,
  configuration-error, Anthropic, Gemini, and `/analyze` behaviors intact.

## Verification

```text
uv run pytest tests/test_chat_transport.py tests/test_vision_context.py tests/test_protocols/test_openai.py tests/test_server/test_openai_contract.py -q
45 passed, 1 warning

uv run pytest tests/test_protocols tests/test_server -q
213 passed, 1 warning

uv run pytest -q
397 passed, 1 warning

uv build
Successfully built dist/seedeep-0.1.0.tar.gz
Successfully built dist/seedeep-0.1.0-py3-none-any.whl

uv run python -m compileall -q deepsee deepsee_server
no output

git diff --check
no output
```

The warning is the existing Starlette TestClient/httpx2 deprecation warning.

## Residual Risks

- No paid request was sent to real DeepSeek or a vision provider. Provider
  compatibility still needs a deployment-time smoke test with real keys.
- Full-history forwarding remains limited to the OpenAI Chat Completions
  endpoint. Anthropic and Gemini still use their existing last-question
  composition path by design.
- The vision cache is process-local and is not shared across multiple workers
  or instances.
- Route integration overlaps existing uncommitted gateway-security work in
  `app.py` and its server tests. Those user-owned changes were preserved and
  were not reset or separated destructively.

# Review Findings Remediation

Date: 2026-08-18
Status: complete

## Implemented

- Moved DSH installer helpers into the release archive, added helper hashes to
  the release manifest, and made the installer bootstrap the verifier from the
  downloaded release asset instead of mutable `main` scripts. The bootstrap
  verifier itself is pinned by SHA-256 in the installer.
- Restricted `DEEPSEE_DSV_VERSION` to a release-version pattern and asserted the
  derived cache path remains below `$DSH_HOME/cache/deepsee-dsv`.
- Hardened provider URL validation against missing hosts, userinfo, query or
  fragment credentials, malformed ports, and whitespace; mapped TOML I/O and
  parse failures to `ConfigError`.
- Validated Anthropic text and image blocks for every message role before
  extracting user content.
- Added FastAPI and Uvicorn to the `dev` extra and refreshed `uv.lock`.
- Clarified that the README contains a public standalone DeepSee reference
  after the DSH workflow, while contributor-only rules remain in
  `CONTRIBUTING.md`.

## Verification

```text
PYTHONPATH=. .venv/bin/pytest -q
509 passed, 1 warning

PYTHONPATH=. .venv/bin/pytest -q tests/test_dsh_installer_script.py \
  tests/test_config.py tests/test_protocols/test_anthropic.py tests/test_release_assets.py
66 passed

uv lock --check
passed

bash -n scripts/install-dsh-dsv.sh
python -m py_compile selected installer/config/protocol files
uv build
passed
```
