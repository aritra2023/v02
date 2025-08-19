#!/usr/bin/env python3
"""
Fallback entry point for Telegram Video Splitter Bot.
Uses standard Telegram Bot API with 20MB file limit.
"""

import asyncio
import logging
import os
from bot_handler import TelegramVideoBot

# Hardcoded credentials for easy deployment
BOT_TOKEN = "8394045984:AAExwf8V262BSEazX29LAKYZYvGfR25bq1w"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the standard bot."""
    try:
        # Ensure clips directory exists
        os.makedirs("clips", exist_ok=True)
        
        logger.info("Starting Telegram Video Splitter Bot (Standard Mode)")
        logger.info("Bot will support files up to 20MB using standard Bot API")
        
        # Initialize and start the standard bot
        bot = TelegramVideoBot(BOT_TOKEN)
        await bot.start()
        
    except Exception as e:
        logger.error(f"Failed to start standard bot: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
