#!/usr/bin/env python3
"""
Primary entry point for Telegram Video Splitter Bot with large file support.
Uses MTProto protocol via Pyrogram for files up to 2GB.
"""

import asyncio
import logging
import os
from large_file_handler import LargeFileHandler

# Hardcoded credentials for easy deployment
API_ID = 14619078
API_HASH = "c90576cc470b4bd4dc08396cfa449833"
BOT_TOKEN = "8394045984:AAExwf8V262BSEazX29LAKYZYvGfR25bq1w"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main entry point for the large file bot."""
    try:
        # Ensure clips directory exists
        os.makedirs("clips", exist_ok=True)
        
        logger.info("Starting Telegram Video Splitter Bot (Large File Support)")
        logger.info(f"API_ID: {API_ID}")
        logger.info("Bot will support files up to 2GB using MTProto protocol")
        
        # Initialize and start the large file handler
        bot = LargeFileHandler(
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
        
        await bot.start()
        logger.info("Bot started successfully!")
        
        # Keep the bot running
        await bot.run()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        # Fallback to standard bot if MTProto fails
        logger.info("Falling back to standard bot...")
        try:
            from bot_handler import TelegramVideoBot
            standard_bot = TelegramVideoBot(BOT_TOKEN)
            await standard_bot.start()
        except Exception as fallback_error:
            logger.error(f"Fallback bot also failed: {fallback_error}")
            raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
