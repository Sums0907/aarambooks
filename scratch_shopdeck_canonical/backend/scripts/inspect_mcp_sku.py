#!/usr/bin/env python3
import json
import sys
import os

from shopdeck.mcp_client import ShopDeckMCPClient

def inspect_mcp_for_sku():
    target_skus = ["101OTTO", "102OTTO", "125BS", "103BS", "117BS"]
    
    try:
        client = ShopDeckMCPClient()
    except Exception as e:
        print(f"Failed to initialize MCP Client: {e}")
        print("Please ensure this is run in an environment with a valid SHOPDECK_MCP_TOKEN.")
        sys.exit(1)
        
    print("Fetching list of tables from MCP...")
    try:
        tables = client.list_tables()
    except Exception as e:
        print(f"Failed to fetch tables: {e}")
        sys.exit(1)
        
    for table_info in tables:
        table_name = table_info.get("table_name")
        if not table_name:
            continue
            
        print(f"\nScanning table: {table_name}")
        query = f"SELECT * FROM {table_name} LIMIT 500"
        try:
            res = client.query_data(query, table_name)
            rows = res.get("rows", []) if isinstance(res, dict) else []
            
            found = False
            for row in rows:
                row_str = json.dumps(row)
                for sku in target_skus:
                    if sku in row_str:
                        print(f"✅ FOUND target SKU '{sku}' in table '{table_name}'!")
                        print("Raw JSON row snippet:")
                        print(json.dumps(row, indent=2))
                        print("-" * 50)
                        
                        # Find exactly which keys hold the SKU
                        def find_keys(data, target, path=""):
                            if isinstance(data, dict):
                                for k, v in data.items():
                                    find_keys(v, target, f"{path}.{k}" if path else k)
                            elif isinstance(data, list):
                                for i, v in enumerate(data):
                                    find_keys(v, target, f"{path}[{i}]")
                            elif str(data) == target:
                                print(f"👉 Exact match found at path: {path}")
                                
                        find_keys(row, sku)
                        found = True
                        break
                if found:
                    break
        except Exception as e:
            print(f"Failed to query {table_name}: {e}")

if __name__ == "__main__":
    inspect_mcp_for_sku()
