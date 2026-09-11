# Context handoff — ShopDeck production hardening session, for a new Gemini agent

Written by: Claude (ShopDeck workspace)
Date: 2026-09-09, end of day
Supersedes: `CONTEXT_HANDOFF_SHOPDECK_WORKSTATION.md` (2026-09-09, earlier today) — that doc
covered the repo split + VPS cutover only. Everything below happened *after* it was written,
in the same repo, same day. Read this one; treat that one as historical background only.

**Read this whole document before touching ShopDeck, Identity, Inventory, or Packing.** A lot
happened today across all four apps, not just ShopDeck, because several bugs turned out to be
the same root cause repeated across apps.

---

## 0. Where things live — read this first, it trips people up

- **ShopDeck's only working source is**
  `/Users/sumatidhingra/Documents/AaramBooks/business_systems/shopdeck`. The old path
  `/Users/sumatidhingra/aarambooks/business_systems/shopdeck` is **permanently defunct** — it
  was ripped apart in the repo split described in the superseded doc. Don't work there, don't
  treat it as a backup, don't reference it in new code or docs.
- ShopDeck's repo is `github.com/Sums0907/aarambooks-shopdeck`, fully separate from the Brain
  monorepo (`github.com/Sums0907/aarambooks`, which is what `~/aarambooks/` on your machine
  and on the VPS root actually is) and separate from Catalog
  (`github.com/Sums0907/aarambooks-catalog`).
- **Catalog is owned by a different agent/session — do not touch its git state or working
  tree.** This has been repeated by the user explicitly more than once; treat it as a hard
  boundary.
- The VPS (`aaramhomes@200.234.39.72`) runs four independent apps side by side under
  `~/aarambooks/`: `business_systems/shopdeck/`, `identity/`, `inventory/`, `packing/` — each
  with its own `docker-compose.prod.yml` + `.env`, each deployed from pre-built GHCR images,
  **no source/git checkout for any of them on the VPS**. `~/aarambooks/` itself is *also* the
  root of an unrelated stray git clone of the Brain monorepo — see §7 below, it's a known
  issue with its own plan, not something to fix ad hoc.

## 1. What shipped today, ShopDeck feature-wise

- **Orders table rebuilt**: the "Order ID" column used to show the wrong ID (the internal
  `order_summary.order_id`) — it now shows `seller_group_id`, which is what actually matters
  operationally. Full rewrite of `backend/api/routers/orders.py` (LEFT JOIN LATERAL
  aggregating seller_group_ids, AWBs, customer info, item/product/SKU summaries, fulfillment
  status, delivery dates, etc. per order) and `frontend/src/screens/Orders.jsx` (grouped
  card-style columns, status/payment filters, AWB copy button). New
  `frontend/src/screens/OrderDrilldown.jsx` for a per-order detail view with a fulfillment
  timeline.
- **Customer search fixed**: previously assumed phone numbers were encrypted/unsearchable —
  they're actually plaintext in `customer_info.customer_number`. `customers.py` rewritten to
  a single unified `search` param covering customer id/phone/AWB/city/state/name.
- **Insights feature built from scratch** (`backend/api/routers/insights.py` +
  `frontend/src/screens/Insights.jsx`): the event tables (`cancellations`,
  `checkout_friction`, `payment_funnel`, `reviews`, `returns_funnel`) were initially dismissed
  as noise — the user correctly pushed back on that, and this feature is the result of
  actually mining them for real business intelligence (cancellation reasons × avg order
  value, checkout error hotspots, review star distribution by product, etc.).

None of this needs redoing. It's live in production, verified against real data.

## 2. The sync engine had a real, silent data-loss bug — fixed, and production was reconciled

`backend/sync/sync_shopdeck_mcp_data.py`'s `query_data()` calls were missing the required
`dateRange` parameter. The MCP tool doesn't raise on a missing required param — it returns a
validation-error response shaped like a normal response, and the old code didn't check for
that shape, so it silently treated every one of those errors as "0 rows synced" and moved on.
This had been happening continuously; the local/production databases had drifted out of
parity with the real source data for an unknown period.

Fixed: `start_date`/`end_date` now always passed explicitly; malformed/error-shaped responses
now `raise RuntimeError` instead of being swallowed; added within-batch dedup-to-most-recent
logic in `upsert_records` (a stale record could otherwise win over a newer one in the same
batch). **A full reconciliation pass was then run against production** to backfill everything
that drifted while this bug was live — this was explicitly required ("full parity"), not
optional, and has been done.

If you're asked to touch this file again: the `dateRange` requirement is easy to reintroduce
by accident if you add a new `query_data()` call elsewhere without copying the existing
pattern — check `list_tables`/`query_data`'s actual required params via the MCP tool schema,
don't assume.

## 3. Production infrastructure bugs found and fixed — full detail is in the runbook, not repeated here

Everything below is now written up as a proper postmortem, with root cause / fix / prevention
check, in
**`/Users/sumatidhingra/Documents/AaramBooks/business_systems/shopdeck/docs/master_deployment_runbook.md`
§6.** Read that section rather than re-deriving any of this from scratch:

- §6.1 — deployment model migration (local-build → GHCR images-only) is fully done for
  ShopDeck; the runbook itself was stale describing the old model and has been rewritten.
- §6.2 — **all four apps'** `mac_to_vps_deploy.sh` were silently reporting "success" on every
  run regardless of whether the VPS actually did anything, because `set -e` in the local
  script doesn't propagate into a separate SSH heredoc's remote shell. Fixed in all four —
  each now has its own remote `set -e` + `ERR` trap, plus color-coded output
  (red=fail/yellow=warn/green=ok) and a printed post-deploy container-uptime line. **Trust
  that uptime line, not the green checkmark alone** — that's the one signal that actually
  proves a deploy did something.
- §6.3 — ShopDeck's production nginx was serving a stale static `dist/` off disk instead of
  proxying to the running frontend container. Fixed (now `proxy_pass`es to `127.0.0.1:8211`);
  the stale directory was deleted after confirming nothing referenced it.
- §6.4 — duplicate `Access-Control-Allow-Origin` headers (set by both the app and nginx) were
  breaking CORS enforcement in some browsers. Fixed — nginx's copy removed.
- §6.5 — `docker compose ls`/`ps` report a **cached, stale** config file path from
  container-creation-time labels, not a live re-read of the file. Do not trust it as proof a
  compose file currently exists — `ls -la`/`cat` the file directly. This bit both Identity and
  Packing during today's investigation.
- §6.6 — a self-caught mistake: recreated Packing's containers with `up -d` without `pull`
  first, which silently reused a days-old cached image. Caught via a `Last-Modified` header
  mismatch, corrected. The deploy script's `pull`-before-`up -d` ordering exists specifically
  to prevent this from ever being a manual judgment call again.
- §6.8 — same class of bug as §2 above, this is the sync-engine writeup with the exact
  numbers.
- §6.9 — a unique-index migration had been silently failing (logged at `.debug`, invisible)
  because duplicate rows already existed under the intended key.
  `customer_info`/`ndr_action_log`/`shipment_ndr_reports` were deduped in production (668 /
  263 / 1,281 rows respectively) and the 3 missing indexes created. Log level raised to
  `.warning` so this can't go unnoticed again.
- §6.10 — **the big one.** A reported "still logged in as admin after logout" issue in Safari
  turned into a multi-layer investigation. Two *real* code bugs were found and fixed along the
  way (a `/logout` route that had never actually shipped to production; a race condition
  between the auto-refresh-token logic and an explicit logout call). The actual root cause of
  the specific reported symptom, though, was a **stale Service Worker registered in that one
  browser** from an old build — nothing to do with server code at all, confirmed by checking
  the actual running bundle hash client-side. Resolved by the user clearing it from Safari's
  Privacy settings. The two real code fixes remain in place; a `pageshow`/`event.persisted`
  bfcache-reload guard was also added to both ShopDeck's and Identity's frontends as a related
  hardening, since Safari doesn't reliably honor `Cache-Control: no-store` for bfcache the way
  Chromium does. **If this class of "stale behavior despite a clean deploy" comes up again,
  check the actual running bundle hash in that browser's console early** — it would have saved
  most of the investigation time here.
- §6.11 — Packing had never actually been fully cut over to the GHCR-images model (no compose
  file present on the VPS at all). Fixed. Along the way, discovered 36MB of uploaded shipping
  label files sitting in the container's writable layer with **no persistent volume backing
  them** — backed them up before recreating the container, then restored them into a proper
  named volume (`packing_packer_uploads`) so this can't happen again.

## 4. Deploy script hardening applied to all four apps identically

`mac_to_vps_deploy.sh` in ShopDeck, Identity (`AaramIdentity/`), Inventory (`Aaram_Inventory/`),
and Packing (`AaramPackingApp/`) all now share the same pattern: `set -e` + `ERR` trap locally
*and* inside the SSH heredoc separately, ANSI color helpers (`section`/`step`/`ok`/`warn`/
`fail`/`info`), the GitHub Actions run watched live with `gh run watch --exit-status` before
the VPS is touched at all, and a final container-uptime verification line. If you write a new
deploy script for another app, copy this pattern rather than starting from scratch — it exists
because of §6.2 above, a real production issue that went unnoticed for an extended period.

## 5. Two other apps got the same nginx caching fix as ShopDeck

Packing's `packer-web`/`admin-web` and Inventory's frontend had the same class of stale-cache
risk as §6.3 above (no `Cache-Control: no-store` on the SPA shell, so a browser or intermediate
cache could keep serving an old bundle indefinitely after a deploy). Both now set `no-store` on
the shell HTML while keeping long-cache `immutable` headers on hashed asset files. Packing
needed a `.dockerignore` change too — `nginx.conf` had to be excluded from `.dockerignore`'s
blanket exclusion of everything else, since `Dockerfile` needs an explicit `COPY nginx.conf ...`
for it, and `.dockerignore` excludes from the *whole build context*, not just an unqualified
`COPY .`.

## 6. The Brain-monorepo stray git clone on the VPS — has a plan, not yet executed

Unrelated discovery made while investigating one of the above: `~/aarambooks/` on the VPS is
*also* a full git clone of the Brain monorepo (`.git` present, 761 tracked files, origin
`github.com/Sums0907/aarambooks.git`), sitting alongside the four apps' real untracked deploy
folders in the same directory. It has never actually been deployed (no containers read from
it) but something has been running `git pull` against it roughly daily — mechanism
unidentified.

Full plan, reviewed and updated today with concrete safety gaps closed (backup verification,
deletion-completeness check, per-step `cd` discipline, all four apps checked in verification
instead of three), lives at
**`/Users/sumatidhingra/aarambooks/docs/claude/VPS_CLEANUP_PLAN_BRAIN_MONOREPO_CLONE.md`**.
**Not executed yet.** Its own Open Question 1 (what's running the recurring `git pull`) is
still unresolved — this session ruled itself out as the source but could not rule out a
separate, actively-working Brain/Catalog session that may hold a persistent connection to this
VPS. Confirm with whoever owns that before running Step 3 of that plan for real; deleting the
clone out from under an active session would be a real regression, not just tidiness.

## 7. Things that are genuinely done — don't redo them

- Orders/Customers/Insights features — live, verified against real data.
- Sync engine bug fix + full production reconciliation — done.
- ShopDeck nginx proxy fix, duplicate CORS header fix — done, verified via curl.
- Logout saga's two real code fixes (missing route, refresh/logout race) — done, live.
- Packing's GHCR cutover + uploads volume fix — done, verified.
- Deploy script hardening across all four apps — done.
- ShopDeck's `master_deployment_runbook.md` — fully rewritten today to match the current
  architecture and to include every postmortem above; treat it as current, not the old
  build-from-source description.
- VPS cleanup plan for the stray Brain clone — reviewed and rewritten with the gaps closed,
  but explicitly **not run**. Don't assume it's done because the doc looks polished.
