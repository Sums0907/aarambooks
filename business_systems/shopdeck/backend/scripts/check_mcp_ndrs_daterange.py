import asyncio
from shopdeck.mcp_client import ShopDeckMCPClient

def main():
    client = ShopDeckMCPClient()
    awbs = ["24699810620701", "372194722212", "142285241663445"]
    in_clause = ", ".join(f"'{awb}'" for awb in awbs)
    
    end_date = "2026-09-08T00:00:00Z"
    start_date = "2026-01-01T00:00:00Z"
    
    print("\nChecking ndr_action_log in MCP directly...")
    ndr_res = client.query_data(
        f"SELECT awb_no FROM ndr_action_log WHERE awb_no IN ({in_clause})", 
        "ndr_action_log",
        start_date=start_date,
        end_date=end_date
    )
    rows = ndr_res.get('rows', []) if isinstance(ndr_res, dict) else []
    for r in rows:
        print(f"MCP AWB in action log: {r['awb_no']}")
    if not rows:
        print("MCP returned NO rows for these AWBs in ndr_action_log.")

if __name__ == "__main__":
    main()
