# Shopee Force Open — Token & Headers Integration Report

**Overview**
- **Purpose:** Document how authentication tokens and HTTP headers from `webshopee_api_client.py` are reused by `refactored.py` to call Shopee internal APIs.
- **Scope:** Token extraction (`get_auth_tokens` / `extract_auth_tokens`), header construction (`get_shopee_headers`), and validation (`validate_token`).

**Key Functions Reused**
- **get_auth_tokens / extract_auth_tokens:** Extracts `shopee_tob_token` and `shopee_tob_entity_id` from an active Selenium `driver`. Supports `return_json` for structured output. Used by `run_force_open` to obtain the primary `tob_token` and `merchant_entity_id`.
- **get_shopee_headers:** Builds the request headers (including `Cookie`) required for Shopee Food API requests. Accepts `tob_token`, `entity_id`, and an optional `base_cookies_dict` to preserve other cookies.
- **validate_token:** Lightweight API check to confirm a token works against the stores search endpoint. Useful for preflight checks or health monitoring.
- **get_cookies_dict / extract_tokens_from_driver:** Small helpers used by `get_auth_tokens` to collect and convert Selenium cookies.

**How `refactored.py` Integrates These**
- `run_force_open` calls `get_auth_tokens(driver=session.driver, merchant_name=...)` to attempt extraction from the current browser session.
- If extraction fails, `run_force_open` uses a fallback `BrowserSession` (via `driver_creator`) to create a temporary browser, ensure login, and call `get_auth_tokens(..., return_json=True)` to retrieve/store tokens.
- `get_shopee_headers` is called with the extracted `tob_token` plus either the merchant-level `merchant_entity_id` (for store search) or the per-store `store_id` (for store-level actions). This mirrors how the original UI would set `shopee_tob_entity_id` for the specific store context.
- `process_store_via_api` uses `get_shopee_headers(tob_token, entity_id)` and then POSTs to the appropriate endpoints (`/opening-status/action/open` or `/opening-status/action/pause`).

**Important Integration Notes & Rationale**
- Merchant-level vs Store-level `entity_id`:
  - Use the merchant `merchant_entity_id` when calling the store search (`/api/seller/stores/search`).
  - Use the store's `id` as `entity_id` for store-specific open/pause actions where `refactored.py` passes `entity_id=store_id` to `get_shopee_headers`.
- Token lifetime & caching:
  - Tokens should be treated as short-lived session artifacts. `get_auth_tokens` returns fresh tokens from the browser. Consider saving to `data/cache/shopee_auth_tokens.json` (or an encrypted store) when `return_json=True` to avoid requiring browser extraction on every run.
- Validation & retry:
  - Call `validate_token` after extraction to ensure the token is usable before making many store requests.
  - `refactored.py` already implements a fallback browser extraction; keep that flow and add an explicit `validate_token` step for early failure detection.

**Error Handling & Rate Limiting**
- Respect API timeouts (configured via `API_TIMEOUT`) and handle `requests` exceptions (timeouts, connection errors). `refactored.py` already distinguishes these cases—keep that behavior.
- Implement small random delays between API calls (already present as `RATE_LIMIT_DELAY_MIN/MAX`) to reduce chance of throttling.

**Security & Logging**
- Do not log full `shopee_tob_token` or sensitive cookie values. Log only masked snippets (e.g., first/last chars) if needed for debugging.
- If caching tokens, store them encrypted or restrict file permissions to the executing user.

**Testing Recommendations**
- Local dry-run: run `run_force_open(..., dry_run=True)` to exercise token/header flow without sending state-changing requests.
- Unit tests: stub `get_shopee_headers` and `get_auth_tokens` to verify `refactored.py` passes expected values (merchant vs store entity id) to the API call helpers.

**Next Steps / Improvements**
- Centralize token cache and TTL logic in `modules/shopee/api_utils.py` (e.g., `cache_tokens()` / `get_cached_tokens()` helpers).
- Add an optional `validate_on_extract` flag to `get_auth_tokens` to run `validate_token` automatically.
- Add instrumentation/metrics for token extraction success rate and API error rates to improve reliability.

---
Generated for integration with `modules/shopee/force_open/refactored.py` — describes how tokens and headers are used and recommended best practices.



# Progression: Gaps & Next Steps vs `webshopee_api_client.py`

This document lists what is missing in the current `refactored.py` / `api_utils.py` flow when compared to the more feature-rich `webshopee_api_client.py`, plus prioritized next steps.

Missing / Gaps
- Async session & client:
  - No `BaseAiohttpSession`-style async client; the codebase uses synchronous `requests` for force-open operations.
- Cookie/token cache with TTL:
  - `webshopee_api_client.py` uses a `TTLCache` for cookies. `api_utils.py` lacks a persistent cache with TTL and optional encryption.
- Concurrency primitives:
  - No request semaphore or centralized concurrency control for high-volume endpoints.
- Robust retry/backoff:
  - Missing exponential backoff and configurable retry attempts present in `webshopee_api_client.py`.
- Expanded endpoint coverage:
  - Many endpoints (orders, notifications, dishes, modifiers, operational hours, cancel/ready) are present in `webshopee_api_client.py` but not in `refactored.py`.
- Header variants & host handling:
  - Multiple header builders in `webshopee_api_client.py` (food vs notification). `get_shopee_headers` should support variants.
- DRY_RUN, config-driven timeouts, and metrics parity:
  - `webshopee_api_client.py` references config-driven flags (timeouts, DRY_RUN, retries). Bring same config parity to `api_utils.py` and `refactored.py`.

Priority Next Steps
- P1 — Token cache + validate_on_extract (1–2 days)
  - Implement file-backed TTL cache for tokens in `modules/shopee/api_utils.py`.
  - Add `validate_on_extract` flag to optionally call `validate_token` immediately after extraction.
- P2 — Retry/backoff + timeout centralization (1 day)
  - Add a retry decorator or helper used by `process_store_via_api`.
  - Centralize `API_TIMEOUT` and rate-limit delays in config.
- P3 — Header variant support (0.5–1 day)
  - Extend `get_shopee_headers` to accept a `purpose` or `variant` param (e.g., `food`, `notification`).
- P4 — Decide sync vs async and scaffold adapter (3–5 days)
  - If async adoption chosen, scaffold a small adapter to call `WebShopeeAPIClient` for heavy endpoints and migrate.
- P5 — Expand endpoint implementations & tests (2–4 days)
  - Add missing endpoints as needed (dishes, modifiers, orders, notifications, operational hours).
  - Add unit/integration tests; add DRY_RUN handling.

Security & Observability
- Mask tokens in logs; avoid writing raw tokens to logs or public files.
- If caching tokens, encrypt at rest or use restrictive file permissions.
- Add basic metrics (extraction success, API error rates) for operational visibility.

Suggested Immediate Action
- I can implement P1 (token cache + validate_on_extract) next — shall I proceed with that change now?


# Tests To Add — `force_open` Integration

This file lists recommended unit and integration tests for `modules/shopee/api_utils.py`, `modules/shopee/force_open/refactored.py`, and the scheduler.

Unit tests (fast, isolated):
- `test_get_shopee_headers_variants()` — verify header outputs for food/notification variants and cookie formatting. ✅
- `test_extract_tokens_from_driver()` — simulate Selenium cookie lists; assert correct token/entity extraction. ✅
- `test_get_cookies_dict_none_driver()` — ensure empty dict returned for `None` driver. ✅
- `test_validate_token_success_and_failure()` — mock `requests.post` to return successful and failing responses; assert boolean result.
- `test_process_store_via_api_responses()` — mock open/pause endpoints: success, non-zero code, timeout, connection error. ✅
- `test_get_store_status_via_api_match_by_id_and_fallback()` — mock search responses to test ID match and fallback-to-first behavior. 

Integration tests (slower, end-to-end with mocks):
- `test_run_force_open_dry_run_no_changes()` — run `run_force_open(..., dry_run=True)` with mocked `fetch_board_items`; assert no state-changing requests.
- `test_run_force_open_full_flow_with_fallback_tokens()` — simulate initial token extraction failure; ensure fallback `BrowserSession` obtains tokens and they are used in API calls. ✅
- `test_run_force_open_concurrent_processing_behaviour()` — use multiple stores, mock status and API calls, assert stats categorization (forced_open, already_open, failed). ✅
- `test_discord_notification_triggered()` — verify `send_discord_notification` called only when forced opens/closes exist and payload fields are correct. ✅
- `test_state_cache_update_after_run()` — run scheduler `run_all_merchants` with mocked `fetch_board_items` and file I/O; assert state cache file updated.

Fixtures & helpers recommended:
- `fake_driver_with_cookies` — fixture to simulate `driver.get_cookies()` returns.
- `mock_requests_post` / `mock_requests_session` — helpers to simulate `requests` behavior including timeouts and connection errors.
- `tmp_token_cache` — temporary file-backed cache fixture to isolate token cache during tests.

Testing order suggestion:
1. Add the unit tests for `api_utils.py` helpers and `process_store_via_api`.
2. Add integration tests for `run_force_open` in `dry_run` mode.
3. Add the fallback/token extraction integration test and scheduler state tests.
