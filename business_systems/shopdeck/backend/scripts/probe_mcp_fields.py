#!/usr/bin/env python3
"""
Probe the live MCP for order_line_items field names.
Run with: set -a && source .env && set +a && python3 probe_mcp_fields.py
"""
import json
import sys

from shopdeck.mcp_client import ShopDeckMCPClient

def main():
    client = ShopDeckMCPClient()

    print("=== Fetching 5 rows from order_line_items ===")
    res = client.query_data("SELECT * FROM order_line_items LIMIT 5", "order_line_items")
    rows = res.get("rows", []) if isinstance(res, dict) else []

    if not rows:
        print("No rows returned. Trying order_summary...")
        res = client.query_data("SELECT * FROM order_summary LIMIT 5", "order_summary")
        rows = res.get("rows", []) if isinstance(res, dict) else []

    if not rows:
        print("No data from MCP at all. Check token.")
        sys.exit(1)

    row = rows[0]
    print(f"\nTotal fields in first row: {len(row)}")
    print("\n=== ALL FIELD NAMES + VALUES ===")
    for k, v in sorted(row.items()):
        val_str = str(v)[:80] if v is not None else "NULL"
        print(f"  {k:45s} = {val_str}")

    print("\n=== FIELDS THAT LOOK LIKE SKU/PRODUCT CODES (non-null, short string) ===")
    for k, v in sorted(row.items()):
        if v is None:
            continue
        val_str = str(v)
        # Short alphanumeric codes like 101BS, 125OTTO etc
        if len(val_str) <= 30 and any(c.isdigit() for c in val_str) and any(c.isalpha() for c in val_str):
            print(f"  👉 {k:45s} = {val_str}")

    print("\n=== 5 ROWS: sku_id / seller_sku_id / product_code candidates ===")
    candidate_keys = [k for k in row.keys() if any(x in k.lower() for x in ["sku", "product", "item", "code", "variant"])]
    print(f"Candidate keys: {candidate_keys}")
    for i, r in enumerate(rows):
        vals = {k: r.get(k) for k in candidate_keys}
        print(f"  Row {i+1}: {json.dumps(vals, default=str)}")

if __name__ == "__main__":
    main()
