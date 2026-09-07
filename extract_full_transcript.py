from pymongo import MongoClient

def main():
    client = MongoClient("mongodb://localhost:27017")
    db = client.aarambooks_ndr_communications
    
    events = list(db.customer_engagement_events.find(
        {"provider": "EXOTEL", "event_type": "transcript"}
    ).sort("received_at", 1))
    
    transcript_segments = {}
    
    for e in events:
        payload = e.get("payload", {})
        payload_events = payload.get("events", [])
        for ev in payload_events:
            if ev.get("event_type") == "transcript":
                data = ev.get("event_data", {})
                seq = data.get("sequence", 0)
                segments = data.get("transcript_segments", [])
                
                # Only keep the ones where all are is_final=True (or latest update)
                # Actually, let's just keep the last received one per sequence
                transcript_segments[seq] = segments
                
    print("\n--- FINAL TRANSCRIPT ---\n")
    for seq in sorted(transcript_segments.keys()):
        for seg in transcript_segments[seq]:
            if seg.get("is_final"):
                speaker = seg.get("speaker", "UNKNOWN").upper()
                text = seg.get("text", "")
                print(f"{speaker}: {text}")

if __name__ == "__main__":
    main()
