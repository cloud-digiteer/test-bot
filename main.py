from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import os
from dotenv import load_dotenv
import requests
import logging
import uuid

# Load environment variables
load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "myverifytoken")
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
DX_API_SEND_MESSAGE = os.getenv("DX_API_SEND_MESSAGE")

FB_MESSENGER_API = "https://graph.facebook.com/v21.0/me/messages"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Temporary in-memory map (for development only)
sender_map = {}  # key: chat_id (or task_id), value: sender_id

@app.get("/")
def root():
    return {"status": "Running"}

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

                    if message_text: 
                        # Store sender_id for callback
                        sender_map[1] = sender_id  # Replace with dynamic chat_id or task_id if needed

                        # Send message to DX API
                        dx_payload = {
                            "chat_id": str(uuid.uuid4()),
                            "user_message": message_text,
                            "file_ids": ["fdb6b0e8-6091-42e9-b2de-aeb535d0026b", "723cd06a-d51d-4638-acd2-6efc7b024987"],
                            "file_urls": [],
                            "callback_type": "messenger"
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

    return {"status": "ok"}

@app.post("/dx-result")
async def receive_dx_result(request: Request):
    try:
        data = await request.json()
        logger.info(f"[DX RESULT] Received: {data}")

        ai_response = data.get("ai_response")
        chat_id = data.get("chat_id")

        sender_id = sender_map.get(chat_id)

        if sender_id and ai_response:
            send_payload = {
                "recipient": {"id": sender_id},
                "message": {"text": ai_response},
            }
            headers = {
                "Authorization": f"Bearer {PAGE_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }

            logger.info("Before sending AI reply")
            logger.info(f"Payload to Facebook Messenger: {send_payload}")
            response = requests.post(FB_MESSENGER_API, headers=headers, json=send_payload)
            response.raise_for_status()
            logger.info(f"Sent AI reply to {sender_id}")
            logger.info("After sending AI reply")

        else:
            logger.warning(f"Sender ID not found for chat_id: {chat_id} or missing ai_response")

        return {"status": "received"}

    except requests.RequestException as e:
        logger.error(f"Failed sending AI reply: {e}")
        if e.response is not None:
            logger.error(f"Facebook status code: {e.response.status_code}")
            logger.error(f"Facebook response: {e.response.text}")
