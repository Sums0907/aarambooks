import asyncio
from backend.shopdeck.mcp_client import ShopDeckMCPClient

async def main():
    client = ShopDeckMCPClient(
        url="https://mcp.shopdeck.com/mcp",
        token="sd_mcp_aaram_77x9a_live"
    )
    res = client.query_data("SELECT * FROM shipment_ndr_reports ORDER BY latest_ndr_time DESC LIMIT 5", "shipment_ndr_reports")
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
