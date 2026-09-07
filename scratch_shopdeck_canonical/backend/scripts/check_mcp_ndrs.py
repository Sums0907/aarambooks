import asyncio
from shopdeck.mcp_client import ShopDeckMCPClient

def main():
    client = ShopDeckMCPClient()
    awbs = ["142285240356604", "24699810620701", "372194722212", "142285241663445"]
    in_clause = ", ".join(f"'{awb}'" for awb in awbs)
    
    # 1. Check order_line_items
    print("Checking order_line_items in MCP...")
    oli_res = client.query_data(f"SELECT awb_no FROM order_line_items WHERE awb_no IN ({in_clause})", "order_line_items")
    print("OLI rows:", len(oli_res.get('rows', [])) if isinstance(oli_res, dict) else oli_res)
    
    # 2. Check shipment_ndr_reports directly
    print("\nChecking shipment_ndr_reports in MCP directly...")
    ndr_res = client.query_data(f"SELECT awb_no, latest_ndr_time, latest_ndr_reason FROM shipment_ndr_reports WHERE awb_no IN ({in_clause})", "shipment_ndr_reports")
    rows = ndr_res.get('rows', []) if isinstance(ndr_res, dict) else []
    for r in rows:
        print(f"MCP AWB: {r['awb_no']}, Time: {r['latest_ndr_time']}, Reason: {r['latest_ndr_reason']}")
    if not rows:
        print("MCP returned NO rows for these AWBs in shipment_ndr_reports.")

if __name__ == "__main__":
    main()
