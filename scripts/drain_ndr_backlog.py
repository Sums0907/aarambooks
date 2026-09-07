#!/usr/bin/env python3
"""
NDR Backlog Drainer
Fetches all existing NDR events from the ShopDeck BS API and pushes them
to the Brain's /events/ndr endpoint for immediate processing.
Run this once to drain the backlog. New events are handled via the push webhook.

Usage (from aarambooks/ root):
    python3 scripts/drain_ndr_backlog.py
"""
import httpx
import asyncio
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SHOPDECK_API = "http://localhost:8200"  # ShopDeck BS local server (start_shopdeck.sh)
BRAIN_API    = "http://localhost:8000"  # Brain local server

# Load bearer token from ShopDeck auth state
auth_file = "business_systems/shopdeck/.auth_state.json"
token = None
if os.path.exists(auth_file):
    with open(auth_file) as f:
        token = json.load(f).get("access_token")
if not token:
    token = os.environ.get("SHOPDECK_ACCESS_TOKEN", "")

HEADERS = {"Authorization": f"Bearer {token}"} if token else {}


async def drain():
    async with httpx.AsyncClient(timeout=30.0) as client:
        page = 1
        limit = 100
        total_pushed = 0
        total_pages = None

        while True:
            logging.info(f"📄 Fetching page {page} of NDR events from ShopDeck BS...")
            resp = await client.get(
                f"{SHOPDECK_API}/api/v1/ndr",
                params={"page": page, "limit": limit},
                headers=HEADERS
            )
            if resp.status_code != 200:
                logging.error(f"❌ ShopDeck API returned {resp.status_code}: {resp.text[:200]}")
                break

            data = resp.json()
            rows = data.get("data", [])
            meta = data.get("meta", {})

            if total_pages is None:
                total = meta.get("total", 0)
                total_pages = -(-total // limit)  # ceiling division
                logging.info(f"📦 Total NDRs in ShopDeck BS: {total} ({total_pages} pages)")

            if not rows:
                logging.info("✅ All pages processed.")
                break

            awb_nos = [r["awb_no"] for r in rows if r.get("awb_no")]
            logging.info(f"   → Pushing {len(awb_nos)} AWBs to Brain: {awb_nos[:3]}...")

            brain_resp = await client.post(
                f"{BRAIN_API}/events/ndr",
                json={"awb_nos": awb_nos, "source": "ndr_backlog_drain"}
            )

            if brain_resp.status_code == 200:
                result = brain_resp.json()
                logging.info(f"   ✅ Brain acknowledged {result.get('processed')} AWBs (page {page})")
                total_pushed += len(awb_nos)
            else:
                logging.error(f"   ❌ Brain returned {brain_resp.status_code}: {brain_resp.text[:200]}")

            if page >= (total_pages or 1):
                break
            page += 1

        logging.info(f"\n🎉 Backlog drain complete. Total AWBs pushed to Brain: {total_pushed}")


if __name__ == "__main__":
    asyncio.run(drain())
