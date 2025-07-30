from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import os
from dotenv import load_dotenv
import requests

load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "myverifytoken")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
FB_MESSENGER_API = "https://graph.facebook.com/v18.0/me/messages"

@app.get("/")
def root():
    return {"status": "Running"}

@app.get("/webhook")
async def verify(request: Request):
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("[Webhook Verified]")
        return PlainTextResponse(content=challenge, status_code=200)
    else:
        return PlainTextResponse("Forbidden", status_code=403)

@app.post("/webhook")
async def handle_messages(request: Request):
    body = await request.json()
    if body.get("object") == "page":
        for entry in body.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if "message" in messaging_event:
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"].get("text")
                    print(f"Message from {sender_id}: {message_text}")

                    if message_text and message_text.lower() == "hello":
                        send_payload = {
                            "recipient": {"id": sender_id},
                            "message": {"text": "How may I help youasdsadsadadasdsaasd?"},
                        }
                        headers = {
                            "Authorization": f"Bearer {PAGE_ACCESS_TOKEN}",
                            "Content-Type": "application/json"
                        }
                        try:
                            response = requests.post(FB_MESSENGER_API, headers=headers, json=send_payload)
                            response.raise_for_status()
                            print(f"Sent reply to {sender_id}")
                        except requests.RequestException as e:
                            print(f"Error sending message: {e}")

    return {"status": "ok"}
