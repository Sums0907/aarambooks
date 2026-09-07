from src.api.webhooks.exotel_webhooks import parse_correlation_metadata, extract_provider_session_id

payload = {
  "account_id": "aaramhomes1",
  "session_id": "4b99de25-0ed3-49bd-ba1c-ca4b927ce608",
  "custom_parameters": {
    "073068cf-1693-4e34-9d00-2ed3dc884698|act_8adcbe6f": "",
    "assistant_version": "v2",
    "bot_version": "v6"
  }
}

eng_id, act_id = parse_correlation_metadata(payload)
print(f"EngID: {eng_id}, ActID: {act_id}")
print(f"SessionID: {extract_provider_session_id(payload)}")
