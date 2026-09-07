import asyncio
import httpx
import json
import os
import subprocess
import sys

# Add project root to PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.shared.config import settings

def listen_to_microphone():
    try:
        import speech_recognition as sr
    except ImportError:
        print("❌ SpeechRecognition not installed. Run: pip install SpeechRecognition pyaudio")
        return None
        
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n🎤 [Microphone Active] Please speak now...")
        r.adjust_for_ambient_noise(source, duration=0.5)
        # Play a ping sound
        print("\a")
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            print("❌ No speech detected.")
            return None
        
    try:
        print("⏳ Processing speech-to-text...")
        text = r.recognize_google(audio)
        print(f"✅ Transcribed: '{text}'")
        return text
    except sr.UnknownValueError:
        print("❌ Could not understand audio.")
        return None
    except sr.RequestError as e:
        print(f"❌ Could not request results; {e}")
        return None

async def conversational_voice_loop(awb_no: str):
    # 2. Fetch encyclopedia from ShopDeck Mock API (running on port 8200)
    shopdeck_url = f"http://127.0.0.1:8200/api/v1/ndr/{awb_no}"
    print(f"\n[Fetching Context from ShopDeck at {shopdeck_url}...]")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(shopdeck_url)
            data = resp.json()
            print("\n[DEBUG] Raw API Response:", json.dumps(data, indent=2))
            
            # Extract Encyclopedia Data
            items = data.get("items", [])
            item_list = "\n".join([f"- {item.get('quantity', 0)}x {item.get('product_name', 'Unknown Product')} (SKU: {item.get('sku_id', 'N/A')}, Code: {item.get('product_code', 'N/A')}) at Rs {item.get('selling_price', 0.0)}" for item in items])
            
            amount = data.get("cod_amount", 0.0)
            payment_mode = data.get("payment_mode", "UNKNOWN").upper()
            courier = data.get("courier_partner", "the courier")
            ndr_reason = data.get("latest_ndr_reason", "delivery failure")
            customer_name = data.get("customer_name", "Customer")
            order_id = data.get("order_id", "Unknown")
            order_date = data.get("order_date", "Unknown")
            if order_date and order_date != "Unknown":
                order_date = order_date.split("T")[0]
    except Exception as e:
        item_list = "- Unknown items"
        amount = 0
        payment_mode = "UNKNOWN"
        courier = "the courier"
        ndr_reason = "delivery failure"
        customer_name = "Customer"
        order_id = "Unknown"
        order_date = "Unknown"

    system_prompt = f"""Agent:
You are calling {customer_name} regarding a failed delivery for their recent order.

CRITICAL RULES:
1. NEVER say the AWB Number ({awb_no}) or Order ID ({order_id}) to the customer. These are internal tracking codes and sound robotic.
2. Instead of tracking numbers, refer to the actual products they ordered (e.g. "your delivery of 1 Pure Cotton Bedsheet").

--- ENCYCLOPEDIA OF THIS ORDER ---
Order ID: {order_id} (Internal use only)
Order Date: {order_date}
Items Ordered:
{item_list}
Payment Mode: {payment_mode}
Total Amount Due on Delivery: Rs {amount}
Courier Partner: {courier}
Latest Failure Reason: {ndr_reason}
----------------------------------

Your goal is to find out why the delivery failed and ask them if they want to reschedule or cancel.
Keep your responses short, conversational, and natural (1-2 sentences max).
Do NOT act like a robot. Always refer to the items by their product name, not their internal codes."""

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": "Hello?"}]
    
    print("\n📞 [CALL CONNECTED]")
    print("💡 TIP: Say 'bye', 'goodbye', or 'hang up' to end the conversation and generate the report.")
    transcript = ""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            # Get LLM response
            payload = {
                "model": settings.litellm_model,
                "messages": messages,
                "temperature": 0.7
            }
            try:
                resp = await client.post(
                    "http://127.0.0.1:4000/chat/completions", 
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.litellm_api_key}"}
                )
                if resp.status_code != 200:
                    print(f"❌ LLM Error {resp.status_code}: {resp.text}")
                    break
                llm_reply = resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"❌ LLM Exception: {e}")
                break
                
            clean_reply = llm_reply.strip()
            
            print(f"🤖 Agent: {clean_reply}")
            subprocess.run(["say", clean_reply])
            transcript += f"Agent: {clean_reply}\n"
            
            messages.append({"role": "assistant", "content": llm_reply})
            
            user_text = listen_to_microphone()
            if not user_text:
                user_text = "[Customer was silent]"
                
            transcript += f"Customer: {user_text}\n"
            messages.append({"role": "user", "content": user_text})
            
            if "hang up" in user_text.lower() or "goodbye" in user_text.lower() or "bye" in user_text.lower():
                print("\n📞 [CALL ENDED BY CUSTOMER]")
                break
            
    return transcript

async def run_simulation():
    print("========================================")
    print(" AaramBooks NDR Automated Flow Simulator")
    print("========================================")
    
    brain_url = "http://127.0.0.1:8000"
    test_awb = "370909749714" # Known active AWB in the ShopDeck Mock
    
    # STEP 1: Simulate ShopDeck pushing a new NDR event
    print(f"\n[1] Pushing NDR event to Brain for AWB: {test_awb}...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{brain_url}/events/ndr",
                json={"awb_nos": [test_awb], "source": "simulator"}
            )
            print(f"Brain Response: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"❌ Failed to reach Brain Backend: {e}")
        return

    print("\n⏳ Brain is fetching context from ShopDeck, analyzing risk, and generating an outbound message...")
    await asyncio.sleep(2)
    
    # STEP 2: Choose Channel
    print("\n========================================")
    print("Which channel do you want to simulate?")
    print("1. WhatsApp (Text conversation)")
    print("2. IVR (Keypad DTMF press)")
    print("3. Voice AI (Speak into Microphone)")
    channel_choice = input("Enter 1, 2, or 3: ").strip()

    if channel_choice == "3":
        channel = "ivr"
        webhook_url = f"{brain_url}/api/v1/webhooks/ivr"
        
        # Run the conversational loop
        user_reply = await conversational_voice_loop(test_awb)
        
        if not user_reply:
            print("Simulation aborted due to microphone failure.")
            return
            
    elif channel_choice == "2":
        channel = "ivr"
        webhook_url = f"{brain_url}/api/v1/webhooks/ivr"
        print("\n📞 [CUSTOMER'S PHONE RINGS]")
        print("Robot Voice: 'We noticed your order delivery was not completed.'")
        print("Robot Voice: 'Press 1 to attempt delivery tomorrow. Press 2 to cancel.'")
        user_reply = input("\nPress a keypad digit (e.g., 1 or 2): ").strip()
    else:
        channel = "whatsapp"
        webhook_url = f"{brain_url}/api/v1/webhooks/whatsapp"
        print("\n📱 [CUSTOMER'S PHONE]")
        print("WhatsApp Message: 'We noticed your order delivery was not completed. Would you still like us to deliver this order?'")
        user_reply = input("\nType your reply as the customer (e.g., 'Yes, tomorrow at 4 PM'): ").strip()
    
    # STEP 3: Send reply to the Webhook
    print(f"\n[2] Sending customer reply to {channel.upper()} Webhook...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                json={"awb_no": test_awb, "message": user_reply}
            )
            print(f"Webhook Response: {response.status_code}")
            print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"❌ Failed to reach Webhook: {e}")
        return
        
    print("\n⏳ Brain is parsing intent via Qwen LLM and logging the outcome to MongoDB...")
    await asyncio.sleep(4) # Wait for processing
    
    # STEP 4: Generate ATR
    print("\n[3] Generating Morning ATR Report...")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    atr_script = os.path.join(script_dir, "generate_daily_atr.py")
    
    # Run the ATR generator using the same python executable
    import sys
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(script_dir)
    result = subprocess.run([sys.executable, atr_script], capture_output=True, text=True, env=env)
    print(result.stdout)
    if result.stderr:
        print(f"Error generating ATR: {result.stderr}")
        
    print("\n✅ Simulation Complete! Check the 'reports/' directory for your CSV.")

if __name__ == "__main__":
    asyncio.run(run_simulation())
