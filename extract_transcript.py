from pymongo import MongoClient
import json

def main():
    client = MongoClient("mongodb://localhost:27017")
    db = client.aarambooks_ndr_communications
    
    events = list(db.customer_engagement_events.find(
        {"provider": "EXOTEL", "event_type": "transcript"}
    ).sort("timestamp", 1))
    
    transcript_lines = []
    
    for e in events:
        payload = e.get("payload", {})
        speaker = payload.get("Speaker", payload.get("speaker", "UNKNOWN"))
        text = payload.get("Text", payload.get("text", payload.get("transcript", "")))
        if text:
            transcript_lines.append(f"{speaker}: {text}")
                
    if not transcript_lines:
        print("Transcript lines were empty! Let's print raw payloads:")
        for e in events:
            print(json.dumps(e.get("payload", {}), indent=2))
    else:
        print("\n--- TRANSCRIPT ---\n")
        print("\n".join(transcript_lines))
        print("\n------------------\n")

if __name__ == "__main__":
    main()
