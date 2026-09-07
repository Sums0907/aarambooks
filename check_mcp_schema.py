import os
from dotenv import load_dotenv
load_dotenv("/Users/sumatidhingra/aarambooks/business_systems/shopdeck/.env")

from business_systems.shopdeck.mcp_client import ShopDeckMCPClient

def check():
    client = ShopDeckMCPClient()
    tables = client.list_tables()
    for t in tables:
        if t.get('table_name') == 'order_line_items':
            print("Columns in order_line_items on MCP:")
            for c in t.get('columns', []):
                print(f" - {c['name']} ({c['type']})")
            break
            
    res = client.query_data("SELECT * FROM order_line_items LIMIT 1", "order_line_items")
    print("\nSample Row:")
    if res and 'rows' in res:
        print(res['rows'][0])

check()
