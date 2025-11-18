import asyncio
import json
import logging
import re
from datetime import datetime, timezone

from azure.identity import ManagedIdentityCredential
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from microsoft.teams.api import MessageActivity, TypingActivityInput
from microsoft.teams.apps import ActivityContext, App
import uvicorn

from config import Config

config = Config()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
fastapi_app = FastAPI(title="HR Agent Bot")

# Teams app (original)
def create_token_factory():
    def get_token(scopes, tenant_id=None):
        credential = ManagedIdentityCredential(client_id=config.APP_ID)
        if isinstance(scopes, str):
            scopes_list = [scopes]
        else:
            scopes_list = scopes
        token = credential.get_token(*scopes_list)
        return token.token
    return get_token

app = App(
    token=create_token_factory() if config.APP_TYPE == "UserAssignedMsi" else None
)

@app.on_message_pattern(re.compile(r"hello|hi|greetings"))
async def handle_greeting(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle greeting messages."""
    await ctx.send("Hello! How can I assist you today?")


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    await ctx.reply(TypingActivityInput())

    if "reply" in ctx.activity.text.lower():
        await ctx.reply("Hello! How can I assist you today?")
    else:
        await ctx.send(f"You said '{ctx.activity.text}'")


# FastAPI endpoints
@fastapi_app.api_route("/api/messages", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def handle_messages(request: Request):
    """Handle all request types to /api/messages and log raw request data."""

    timestamp = datetime.now(timezone.utc).isoformat()
    method = request.method

    headers = dict(request.headers)
    query_params = dict(request.query_params)

    try:
        body = await request.body()
        body_decoded = body.decode('utf-8')

        try:
            body_json = json.loads(body_decoded) if body_decoded else None
        except json.JSONDecodeError:
            body_json = None
    except Exception as e:
        body_decoded = f"Error reading body: {str(e)}"
        body_json = None

    logger.info("=" * 80)
    logger.info(f"Incoming {method} request to /api/messages")
    logger.info("=" * 80)
    logger.info(f"Timestamp: {timestamp}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Client: {request.client.host if request.client else 'Unknown'}")
    logger.info("-" * 80)
    logger.info("Headers:")
    for key, value in headers.items():
        logger.info(f"  {key}: {value}")
    logger.info("-" * 80)
    logger.info("Query Parameters:")
    logger.info(f"  {query_params if query_params else 'None'}")
    logger.info("-" * 80)
    logger.info("Body (raw):")
    logger.info(f"  {body_decoded if body_decoded else 'Empty'}")
    logger.info("-" * 80)
    if body_json:
        logger.info("Body (JSON):")
        logger.info(f"  {json.dumps(body_json, indent=2)}")
        logger.info("-" * 80)
    logger.info("=" * 80)

    return JSONResponse(
        status_code=200,
        content={
            "status": "received",
            "message": f"{method} request logged successfully",
            "timestamp": timestamp
        }
    )


@fastapi_app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    # Original Teams app start (commented out)
    asyncio.run(app.start())

    # FastAPI server start
    # logger.info("Starting HR Agent Bot FastAPI server...")
    # uvicorn.run(
    #     fastapi_app,
    #     host="0.0.0.0",
    #     port=10000,
    #     log_level="info"
    # )
