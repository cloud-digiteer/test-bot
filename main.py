from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import os
from dotenv import load_dotenv
import requests
import logging 

load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "myverifytoken")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
DX_API_SEND_MESSAGE = os.getenv("DX_API_SEND_MESSAGE")

FB_MESSENGER_API = "https://graph.facebook.com/v18.0/me/messages"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

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
        logger.info("[Webhook Verified]")
        return PlainTextResponse(content=challenge, status_code=200)
    else:
        return PlainTextResponse("Forbidden", status_code=403)
    
@app.post("dx-result")
async def receive_dx_result(request: Request):
    try:
        data = await request.json()
        logger.info(f"[DX RESULT] Received: {data}")
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"ERROR PROCESSING RECEIVING DX RESULT")
        return {"status": "error", "message": str(e)}

@app.post("/webhook")
async def handle_messages(request: Request):
    body = await request.json()
    if body.get("object") == "page":
        for entry in body.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if "message" in messaging_event:
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"].get("text")
                    logger.info(f"Message from {sender_id}: {message_text}")

                    # 1. Send message_text to DX_API_SEND_MESSAGE
                    if message_text:
                        
                        dx_payload = {
                            "chat_id": 1,
                            "user_message": message_text,
                            "file_ids": [],
                            "file_urls": []
                        }
                        try:
                            dx_response = requests.post(
                                DX_API_SEND_MESSAGE,
                                json=dx_payload,
                                timeout=5
                            )
                            dx_response.raise_for_status()
                            logger.info(f"Sent message to DX API: {dx_response.status_code}")
                        except requests.RequestException as e:
                            logger.error(f"Failed to send message to DX API: {e}")

                    # 2. Auto-reply to user if message is "hello"
                    if message_text and message_text.lower() == "hello":
                        send_payload = {
                            "recipient": {"id": sender_id},
                            "message": {"text": "How may I help you?"},  # cleaned text
                        }
                        headers = {
                            "Authorization": f"Bearer {PAGE_ACCESS_TOKEN}",
                            "Content-Type": "application/json"
                        }

                        try:
                            response = requests.post(FB_MESSENGER_API, headers=headers, json=send_payload)
                            response.raise_for_status()
                            logger.info(f"Sent reply to {sender_id}")
                        except requests.RequestException as e:
                            logger.error(f"Error sending message: {e}")

    return {"status": "ok"}