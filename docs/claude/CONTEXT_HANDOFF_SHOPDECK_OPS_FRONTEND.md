# Handoff: ShopDeck BS Operations Frontend (full rebuild)

**From:** Claude Code
**Scope:** `business_systems/shopdeck/` — 2 new backend read endpoints + full frontend rebuild + deployment wiring
**Status:** Built and partially verified. Two verification gaps below need your environment, not mine.
**Nothing committed.** Everything described here is uncommitted in the working tree.

## Why this happened

The user had no visibility into the NDR queue pipeline — the frontend's `NDR` screen only showed
raw `shipment_ndr_reports`, never touching `ndr_queue` / `ndr_engagements` / `ndr_intelligence_results`
at all. That's the whole hardened queue system from `docs/ndr_queue_architecture_and_hardening.md`,
completely invisible in the UI. The ask was a full-scale, deeply-thought-out ops frontend, not a
patch. Plan was reviewed and approved by the user before building (see
`/Users/sumatidhingra/.claude/plans/structured-spinning-pebble.md` if it's still on disk).

## What changed

### Backend — 2 new read-only endpoints, `backend/api/routers/ndr_queue.py` + `repositories/ndr_queue.py` + `schemas/ndr_queue.py`

- `GET /api/v1/ndr/queue` — paginated, filterable by `queue_status`, browses the **full** queue
  (every status), not just `action_ready`. LEFT JOINs `ndr_engagements` (active) +
  `ndr_intelligence_results` + `shipment_ndr_reports` for customer/courier.
- `GET /api/v1/ndr/queue/{awb_no}/history` — every queue attempt for one AWB with its full
  engagement + intelligence detail. Powers the frontend's per-shipment drill-down.
- Same `get_current_user` (`SHOPDECK_VIEW`) auth as every other read route. No changes to any
  write path — `/claim`, `/status`, `/engagements`, `/intelligence_results` are untouched.

**Two real bugs were caught and fixed during this work, both worth knowing about:**

1. `main.py` router registration order: `ndr.router`'s `GET /{awb_no}` is a single-segment
   catch-all under `/api/v1/ndr`. It was registered *before* `ndr_queue_router`, so it silently
   shadowed the new bare `GET /api/v1/ndr/queue` (matching `"queue"` as `awb_no`). Fixed by moving
   `ndr_queue_router`/`intelligence_router`/`engagement_router` registration before `ndr.router`.
   **If you add another bare-prefix GET route under `/api/v1/ndr/queue` in the future, re-check
   this ordering.**
2. `action_parameters`/`source_evidence` from the LEFT JOIN come back as Python `None` (not the
   JSONB default `'{}'`) when no intelligence result exists yet for that engagement. The repo
   methods now normalize `None` → `{}`/`[]` explicitly; a naive `isinstance(x, str)` check alone
   isn't enough.

Both were only caught by running the actual FastAPI app against the live dev Postgres
(`asyncpg` pool, real rows) — not by the existing mocked test suite (`backend/api/tests/test_ndr_queue.py`),
which still shows 15 pre-existing failures unrelated to this change (confirmed via `git stash` —
same 15 fail on `main` with none of this work applied).

**Dependency you should know about:** the AWB drill-down screen also calls the *existing*
`GET /api/v1/ndr/{awb_no}` (unchanged) for order/COD context — `NDRShipmentContext` fields:
`order_id`, `customer_name`, `customer_number`, `drop_pincode`, `ndr_status`, `cod_amount`,
`items[]`, `action_history[]`. I saw `repositories/ndr.py`, `schemas/ndr.py`, and `services/ndr.py`
change on disk while I was working (your concurrent edits) — I didn't touch them or inspect what
changed, but if that schema's shape moved, `frontend/src/screens/ndr/AwbDrilldown.jsx` will need a
matching update.

### Frontend — full rebuild, `frontend/src/`

Auth (`shopdeck-auth.jsx`, `apiClient.js`, `App.jsx`'s `ProtectedRoute`/`AccessDenied`/`AuthProvider`)
was **left completely untouched** — it was already a real, working AaramIdentity SSO integration
and there was no reason to touch it. Verified via `git diff` there's zero change to
`shopdeck-auth.jsx`/`apiClient.js`, and the only auth-adjacent change in `App.jsx` is one more
route wrapped in the existing `<ProtectedRoute>`.

New shared design system (all new files):
- `src/styles/tokens.css` — replaces the old Vite-template `index.css`, which had `#root` capped
  at 1126px and centered — wrong for a sidebar+content ops layout. `index.css` now just
  `@import`s this.
- `src/hooks/useApiQuery.js` — shared fetch/loading/error/poll hook, replaces per-screen
  copy-pasted `useEffect(fetch...)`.
- `src/components/`: `DataTable`, `StatCard`, `StatusBadge` (+ `toneForQueueStatus`,
  `toneForNdrStatus`, `toneForSellerStatus`, `toneForPaymentStatus`, `toneForCallOutcome`,
  `toneForCustomerIntent`, `toneForConfidence`), `Timeline`, `BarRow`, `EmptyState`.
- `src/utils/format.js` — `formatAge`/`formatDateTime`/`formatCurrency`.

**Status-tone mappings are grounded in real distinct values queried from the live dev DB**, not
guessed — e.g. `seller_last_status` really has `delivered/rto_acknowledged/invalid/cancel_initiated/
dispatched/rto_delivered/rto_initiated/created/printed/lost/initiated/enqueued`; `ndr_status` really
has `rto_initiated/delivered/pending/reattempt_requested/ofd/rto_requested`. If you add new status
values upstream, extend the `toneFor*` switch statements in `StatusBadge.jsx` rather than relying
on the `default` fallback.

Screens (all rebuilt, old flat `screens/NDR.jsx` deleted):
- **`screens/ndr/index.jsx` + `AwbDrilldown.jsx`** — the anchor screen. Funnel strip (accurate
  per-status counts via parallel `?queue_status=X&limit=1` calls, not a client-side bucket of one
  page — see `useQueueCounts.js`), a "Needs Attention" panel for `failed_retryable`/
  `permanently_failed`, full worklist with status filter, and a per-AWB drill-down showing two
  side-by-side timelines: the Brain-owned queue engine timeline (from the new `/history` endpoint)
  and the native ShopDeck outreach log (from `ndr_action_log` via the existing context endpoint) —
  deliberately kept visually distinct per the ADR-005 ownership boundary.
- **`screens/Dashboard.jsx`** — real KPI home (queue health, delivery outcome breakdown via
  `/api/v1/ndr?status=X`, order/customer totals, friction signal counts, sync freshness) instead
  of the old `/system/status` ping.
- **`screens/Orders.jsx` / `Customers.jsx`** — **deliberately scoped down** from the original plan.
  `orders.py`/`customers.py` don't currently support filtering by `seller_last_status` or exposing
  order↔customer aggregates, and I didn't add that (see "Explicitly out of scope" below). These
  screens are honest browsers over what those endpoints actually return today.
- **`screens/Events.jsx`** — aggregate funnel view across the 8 event tables (all-time counts +
  top-6 cancellation reasons tallied from the most recent 100 `cancel_reason_events`), with an
  opt-in raw-table inspector reusing the generic `/events/{table}` endpoint.
- **`screens/SyncHealth.jsx`** — now actually compares `last_watermark` age against
  `cadence_minutes` (fresh/lagging/stale), which the API already returned but the old UI never used.

### Deployment — new, **not build-verified**

- `frontend/Dockerfile.prod` (multi-stage: `node:20-slim` build → `nginx:1.27-alpine` serve) +
  `frontend/nginx.conf` (SPA fallback to `index.html`, no-cache on `config.js`).
- `docker-compose.prod.yml`: new `shopdeck-frontend` service, port `8211:80`, same pattern as
  `shopdeck-api`. No `.:/app` volume mount on this one (unlike the Python services) — nginx serves
  the baked `dist/` from the image, so a source bind-mount would shadow it.
- **I could not run `docker compose build` here** — this sandbox can't reach Docker Hub at all
  (even re-pulling an already-cached tag hung until I killed it). The Dockerfile/nginx.conf follow
  the same pattern as the working `aaram_inventory-frontend` image (confirmed via `docker history`
  — nginx alpine base) but need an actual build on a machine with real registry access before
  trusting them.

## Explicitly out of scope (ask the user before touching)

Two things were confirmed via `AskUserQuestion` before building and deliberately kept minimal:
- Backend scope was capped at the 2 `ndr_queue` endpoints above. `orders.py`/`customers.py` were
  **not** given new filters/aggregation, even though the original plan envisioned an order-status
  breakdown and customer-360 view. A small additive change (optional `status`/`payment_status`
  query params on those two routers, mirroring the pattern `ndr.py` already has) would unlock that,
  but wasn't approved and wasn't done.
- Nothing in the NDR queue's write paths (`claim`, `status`, `engagements`, `intelligence_results`)
  was touched.

## What still needs verification (can't be done from this environment)

1. **Authenticated UI click-through.** I confirmed the app builds clean (`npm run build`) and, via
   a real headless-Chromium run, correctly redirects an unauthenticated session to the real
   AaramIdentity login page with zero console errors. I could not go further — minting a valid
   session requires either real credentials or AaramIdentity's private key, and the permission
   classifier correctly blocked both attempts to obtain either. **Someone needs to log in for real
   and click through every screen**, especially the NDR Command Center against non-trivial data
   (the local dev queue currently only has 2 synthetic rows, both `eligible`, so the
   `action_ready`/`failed_retryable`/`permanently_failed` paths in the UI are implemented but
   never actually exercised against real rows yet).
2. **Docker build**, per above.

## Backend endpoints — quick reference for the frontend contract

```
GET /api/v1/ndr/queue?page=&limit=&queue_status=
  -> { data: [QueueListItem...], meta: { total, page, limit } }

GET /api/v1/ndr/queue/{awb_no}/history
  -> [QueueHistoryItem...]   (404 if no queue history for that AWB)
```

Full field lists are in `backend/api/schemas/ndr_queue.py` (`QueueListItem`, `QueueHistoryItem`).
