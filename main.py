import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
from botbuilder.schema import Activity

# Import your handlers (Keep these as they were in your project)
from teams_bot import on_message_activity
from teams_bot import send_suggested_questions
from rag import ask_policy_question
from botframework.connector.auth import AuthenticationConfiguration
from botframework.connector.auth import MicrosoftAppCredentials

# 1. Force the correct configuration
APP_ID = os.getenv("MicrosoftAppId")
APP_PASSWORD =os.getenv("MicrosoftAppPassword")
TENANT_ID = os.getenv("MicrosoftAppTenantId")

# 3. Setup the adapter
settings = BotFrameworkAdapterSettings(
    app_id=APP_ID,
    app_password=APP_PASSWORD,
    channel_auth_tenant=TENANT_ID
)

adapter = BotFrameworkAdapter(settings)
app = FastAPI(title="Caizin Policy RAG Bot")
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.post("/api/messages")
async def messages(req: Request):

    if req.headers.get("content-length") == "0":
        return {"error": "Empty request body"}

    try:
        body = await req.json()
    except Exception:
        return {"error": "Invalid JSON body"}

    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    async def turn_handler(turn_context):

        activity_type = turn_context.activity.type

        # =========================
        # 1️⃣ When conversation starts / bot is added
        # =========================
        if activity_type == "conversationUpdate":

            members_added = turn_context.activity.members_added or []

            for member in members_added:
                # If added member is NOT the bot itself
                if member.id != turn_context.activity.recipient.id:
                    await send_suggested_questions(turn_context)
                    return


        # =========================
        # 2️⃣ When user sends message (typed OR button click)
        # =========================
        elif activity_type == "message":

            user_text = (turn_context.activity.text or "").strip().lower()

            # If user greets or starts conversation
            if user_text in ["hi", "hello", "hey", "start", "menu"]:
                await send_suggested_questions(turn_context)
                return

            # Otherwise → normal RAG flow
            await on_message_activity(turn_context)
            return


        # =========================
        # 3️⃣ Ignore other activity types safely
        # =========================
        else:
            return

    response = await adapter.process_activity(
        activity,
        auth_header,
        turn_handler
    )

    return response or {}


@app.post("/ask")
async def ask(req: Request):
    body = await req.json()
    return {"answer": ask_policy_question(body.get("question"))}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
