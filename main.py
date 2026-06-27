import asyncio
import logging
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", 8080))


async def main():
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN is not set.")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set.")

    from bot.client import bot
    from web.app import app

    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="warning")
    server = uvicorn.Server(config)

    await asyncio.gather(
        server.serve(),
        bot.start(TOKEN),
    )


if __name__ == "__main__":
    asyncio.run(main())
