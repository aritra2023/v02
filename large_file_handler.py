"""
Large File Handler for Telegram Bot using MTProto protocol.
Supports files up to 2GB using Pyrogram client.
"""

import asyncio
import logging
import os
import tempfile
from typing import Dict, Any
from pyrogram.client import Client
from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from video_processor import VideoProcessor

logger = logging.getLogger(__name__)

class LargeFileHandler:
    """Handles large file uploads and processing using MTProto protocol."""
    
    def __init__(self, api_id: int, api_hash: str, bot_token: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.user_states: Dict[int, Dict[str, Any]] = {}
        self.video_processor = VideoProcessor()
        
        # Initialize Pyrogram client
        self.app = Client(
            "video_splitter_bot",
            api_id=self.api_id,
            api_hash=self.api_hash,
            bot_token=self.bot_token,
            workdir="."
        )
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register message and callback handlers."""
        
        @self.app.on_message(filters.command("start"))
        async def start_command(client, message: Message):
            await self._handle_start(message)
        
        @self.app.on_message(filters.command("clip"))
        async def clip_command(client, message: Message):
            await self._handle_clip_command(message)
        
        @self.app.on_message(filters.video)
        async def video_handler(client, message: Message):
            await self._handle_video(message)
        
        @self.app.on_message(filters.text & ~filters.command(["start", "clip"]))
        async def text_handler(client, message: Message):
            await self._handle_text(message)
        
        @self.app.on_callback_query()
        async def callback_handler(client, callback_query: CallbackQuery):
            await self._handle_callback(callback_query)
    
    async def _handle_start(self, message: Message):
        """Handle /start command."""
        welcome_text = """
**Welcome ᴛᴏ Insta Aᴜᴛᴏ Pᴏsᴛɪɴɢ Bᴏᴛ!**

**I ᴄᴀɴ sᴘʟɪᴛ ʏᴏᴜʀ ᴠɪᴅᴇᴏs ɪɴᴛᴏ sᴍᴀʟʟᴇʀ ᴄʟɪᴘs + ᴇᴅɪᴛ + ᴀɴᴅ ᴀᴜᴛᴏ-ᴜᴘʟᴏᴀᴅ ᴛᴏ Instagram**

**Send ᴍᴇ ᴀ ᴠɪᴅᴇᴏ ᴛᴏ ɢᴇᴛ sᴛᴀʀᴛᴇᴅ**
        """
        
        # Create inline keyboard with About and Settings buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("About ᴜs", callback_data="about"),
                InlineKeyboardButton("Settings", callback_data="settings")
            ]
        ])
        
        # Send welcome message with rotated image and buttons
        await message.reply_photo(
            photo="https://files.catbox.moe/2gmodm.jpg",
            caption=welcome_text,
            reply_markup=keyboard
        )
        logger.info(f"User {message.from_user.id} started the bot")
    
    async def _handle_video(self, message: Message):
        """Handle video uploads."""
        user_id = message.from_user.id
        
        # Store video information
        self.user_states[user_id] = {
            "video_message": message,
            "state": "video_uploaded"
        }
        
        # Get video info
        video = message.video
        file_size_mb = video.file_size / (1024 * 1024)
        duration_mins = video.duration // 60
        duration_secs = video.duration % 60
        
        response_text = f"""
📹 **Video ʀᴇᴄᴇɪᴠᴇᴅ!**

**📂 File ɪɴғᴏ:**
**📁 Size:** {file_size_mb:.1f} MB
**⏱️ Duration:** {duration_mins:02d}:{duration_secs:02d}
**📱 Resolution:** {video.width}x{video.height}

**✨ Ready ᴛᴏ sᴘʟɪᴛ ʏᴏᴜʀ ᴠɪᴅᴇᴏ!** 
**Click ᴛʜᴇ ʙᴜᴛᴛᴏɴ ʙᴇʟᴏᴡ ᴏʀ ᴜsᴇ /clip ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ.**
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Create Cʟɪᴘs", callback_data="start_clip")]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard)
        logger.info(f"Video uploaded by user {user_id}: {file_size_mb:.1f}MB, {video.duration}s")
    
    async def _handle_clip_command(self, message: Message):
        """Handle /clip command."""
        user_id = message.from_user.id
        
        if user_id not in self.user_states or "video_message" not in self.user_states[user_id]:
            await message.reply_text("❌ **Please Sᴇɴᴅ ᴀ Vɪᴅᴇᴏ Fɪʀsᴛ Bᴇғᴏʀᴇ Usɪɴɢ /clip!**")
            return
        
        await self._ask_for_duration(message)
    
    async def _handle_callback(self, callback_query: CallbackQuery):
        """Handle callback queries from inline buttons."""
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        logger.info(f"Callback received from user {user_id}: {data}")
        
        if data == "start_clip":
            if user_id not in self.user_states or "video_message" not in self.user_states[user_id]:
                logger.warning(f"User {user_id} clicked clip button but no video state found")
                await callback_query.answer("Please Send ᴀ Vɪᴅᴇᴏ Fɪʀsᴛ!")
                return
            
            logger.info(f"Starting clip process for user {user_id}")
            await callback_query.answer()
            # Pass user_id directly since callback_query.message doesn't have from_user
            await self._ask_for_duration_with_user_id(callback_query.message, user_id)
            
        elif data == "about":
            about_text = """
**About Insta Aᴜᴛᴏ Pᴏsᴛɪɴɢ Bᴏᴛ**

**This ʙᴏᴛ ʜᴇʟᴘs ʏᴏᴜ ᴄʀᴇᴀᴛᴇ Instagram-ʀᴇᴀᴅʏ ᴄᴏɴᴛᴇɴᴛ ғʀᴏᴍ ʏᴏᴜʀ ʟᴏɴɢ ᴠɪᴅᴇᴏs**

**Features:**
**Advanced ᴠɪᴅᴇᴏ sᴘʟɪᴛᴛɪɴɢ ᴛᴇᴄʜɴᴏʟᴏɢʏ**
**High-ǫᴜᴀʟɪᴛʏ ᴏᴜᴛᴘᴜᴛ ᴡɪᴛʜ ᴏʀɪɢɪɴᴀʟ ʀᴇsᴏʟᴜᴛɪᴏɴ**
**Support ғᴏʀ ғɪʟᴇs ᴜᴘ ᴛᴏ 2GB**
**Optimized ғᴏʀ Instagram ғᴏʀᴍᴀᴛs**

**Developer:** **Professional Mᴇᴅɪᴀ Tᴇᴀᴍ**
**Version:** **2.0**
            """
            await callback_query.message.reply_text(about_text)
            await callback_query.answer()
            
        elif data == "settings":
            settings_text = """
**Settings Pᴀɴᴇʟ**

**Current Cᴏɴғɪɢᴜʀᴀᴛɪᴏɴ:**
**Max Fɪʟᴇ Sɪᴢᴇ:** **2GB**
**Output Qᴜᴀʟɪᴛʏ:** **Original**
**Processing Mᴏᴅᴇ:** **Fast (Stream Copy)**
**Auto-Cʟᴇᴀɴᴜᴘ:** **Enabled**

**Note:** **Settings ᴀʀᴇ ᴄᴜʀʀᴇɴᴛʟʏ ᴏᴘᴛɪᴍɪᴢᴇᴅ ғᴏʀ ʙᴇsᴛ ᴘᴇʀғᴏʀᴍᴀɴᴄᴇ**
            """
            await callback_query.message.reply_text(settings_text)
            await callback_query.answer()
    
    async def _ask_for_duration(self, message: Message):
        """Ask user for clip duration."""
        user_id = message.from_user.id if hasattr(message, 'from_user') and message.from_user else message.chat.id
        await self._ask_for_duration_with_user_id(message, user_id)
    
    async def _ask_for_duration_with_user_id(self, message: Message, user_id: int):
        """Ask user for clip duration with explicit user ID."""
        # Ensure user state exists and preserve video_message
        if user_id not in self.user_states:
            self.user_states[user_id] = {}
        
        self.user_states[user_id]["state"] = "waiting_duration"
        logger.info(f"User {user_id} state changed to waiting_duration")
        
        duration_text = """
⏱️ **Clip ᴅᴜʀᴀᴛɪᴏɴ**

**🔹 How ʟᴏɴɢ sʜᴏᴜʟᴅ ᴇᴀᴄʜ ᴄʟɪᴘ ʙᴇ?** 
**Send ᴍᴇ ᴛʜᴇ ᴅᴜʀᴀᴛɪᴏɴ ɪɴ sᴇᴄᴏɴᴅs.**

**📋 Examples:**
**• 30** - **30 sᴇᴄᴏɴᴅ ᴄʟɪᴘs**
**• 60** - **1 ᴍɪɴᴜᴛᴇ ᴄʟɪᴘs**
**• 120** - **2 ᴍɪɴᴜᴛᴇ ᴄʟɪᴘs**
**• 300** - **5 ᴍɪɴᴜᴛᴇ ᴄʟɪᴘs**

**⬇️ Enter ᴅᴜʀᴀᴛɪᴏɴ ɪɴ sᴇᴄᴏɴᴅs:**
        """
        
        await message.reply_text(duration_text)
    
    async def _handle_text(self, message: Message):
        """Handle text messages (duration input)."""
        user_id = message.from_user.id
        text = message.text.strip()
        
        logger.info(f"Text message from user {user_id}: '{text}'")
        
        if user_id not in self.user_states:
            await message.reply_text("❌ **Please Sᴇɴᴅ ᴀ Vɪᴅᴇᴏ Fɪʀsᴛ Usɪɴɢ /start!**")
            return
        
        state = self.user_states[user_id].get("state")
        logger.info(f"User {user_id} state: {state}")
        
        if state == "waiting_duration":
            try:
                duration = int(text)
                if duration <= 0:
                    await message.reply_text("❌ **Duration ᴍᴜsᴛ ʙᴇ ᴀ ᴘᴏsɪᴛɪᴠᴇ ɴᴜᴍʙᴇʀ!**")
                    return
                
                if duration > 3600:  # 1 hour max
                    await message.reply_text("❌ **Duration ᴛᴏᴏ ʟᴏɴɢ!** Mᴀxɪᴍᴜᴍ ɪs 3600 sᴇᴄᴏɴᴅs (1 ʜᴏᴜʀ).")
                    return
                
                # Start processing
                await self._process_video(message, duration)
                
            except ValueError:
                await message.reply_text("❌ **Please Eɴᴛᴇʀ ᴀ Vᴀʟɪᴅ Nᴜᴍʙᴇʀ ғᴏʀ Dᴜʀᴀᴛɪᴏɴ!**")
        
        else:
            await message.reply_text("❌ **I Dᴏɴ'ᴛ Uɴᴅᴇʀsᴛᴀɴᴅ.** Pʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠɪᴅᴇᴏ ᴏʀ ᴜsᴇ /start!")
    
    async def _process_video(self, message: Message, duration: int):
        """Process the video and split into clips."""
        user_id = message.from_user.id
        video_message = self.user_states[user_id]["video_message"]
        
        # Send processing message
        status_msg = await message.reply_text("🔄 **Processing Yᴏᴜʀ Vɪᴅᴇᴏ...**\n\n⏳ **Downloading Vɪᴅᴇᴏ...**")
        
        try:
            # Download video
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_path = temp_file.name
            
            await video_message.download(file_name=temp_path)
            await status_msg.edit_text("🔄 **Processing Yᴏᴜʀ Vɪᴅᴇᴏ...**\n\n✅ **Download Cᴏᴍᴘʟᴇᴛᴇ**\n⏳ **Splitting Vɪᴅᴇᴏ...**")
            
            # Process video
            output_dir = f"clips/user_{user_id}"
            os.makedirs(output_dir, exist_ok=True)
            
            clip_files = await self.video_processor.split_video(
                input_path=temp_path,
                output_dir=output_dir,
                segment_duration=duration
            )
            
            await status_msg.edit_text("🔄 **Processing Yᴏᴜʀ Vɪᴅᴇᴏ...**\n\n✅ **Download Cᴏᴍᴘʟᴇᴛᴇ**\n✅ **Video Sᴘʟɪᴛ Cᴏᴍᴘʟᴇᴛᴇ**\n⏳ **Uploading Cʟɪᴘs...**")
            
            # Upload clips
            for i, clip_path in enumerate(clip_files, 1):
                try:
                    caption = f"📹 **Clip {i}/{len(clip_files)}** • **Duration:** {duration}s ᴇᴀᴄʜ • **Quality:** ᴏʀɪɢɪɴᴀʟ"
                    await message.reply_video(
                        video=clip_path,
                        caption=caption
                    )
                    
                    # Update progress
                    progress = f"⏳ **Uploading Cʟɪᴘs...** ({i}/{len(clip_files)})"
                    await status_msg.edit_text(f"🔄 **Processing Yᴏᴜʀ Vɪᴅᴇᴏ...**\n\n✅ **Download Cᴏᴍᴘʟᴇᴛᴇ**\n✅ **Video Sᴘʟɪᴛ Cᴏᴍᴘʟᴇᴛᴇ**\n{progress}")
                    
                except Exception as e:
                    logger.error(f"Failed to upload clip {i}: {e}")
                    await message.reply_text(f"❌ **Failed ᴛᴏ Uᴘʟᴏᴀᴅ Cʟɪᴘ {i}:** {str(e)}")
            
            # Success message
            await status_msg.edit_text(f"✅ **Processing ᴄᴏᴍᴘʟᴇᴛᴇ!**\n\n📹 **{len(clip_files)} Clips ꜱᴇɴᴛ ꜱᴜᴄᴄᴇꜱꜱғᴜʟʟʏ!**\n\n🎬 **Thank ʏᴏᴜ ғᴏʀ ᴜsɪɴɢ Video Sᴘʟɪᴛᴛᴇʀ Bᴏᴛ!**")
            
            # Cleanup
            await self._cleanup_files([temp_path] + clip_files)
            
            # Reset user state
            self.user_states[user_id] = {"state": "idle"}
            
            logger.info(f"Successfully processed video for user {user_id}: {len(clip_files)} clips")
            
        except Exception as e:
            logger.error(f"Video processing failed for user {user_id}: {e}")
            error_msg = str(e)[:200] + "..." if len(str(e)) > 200 else str(e)
            await status_msg.edit_text(f"❌ **Processing Failed!**\n\nError: {error_msg}")
            
            # Cleanup on error
            try:
                if 'temp_path' in locals() and temp_path:
                    await self._cleanup_files([temp_path])
            except Exception as cleanup_error:
                logger.warning(f"Cleanup failed: {cleanup_error}")
    
    async def _cleanup_files(self, file_paths: list):
        """Clean up temporary files."""
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup file {file_path}: {e}")
    
    async def start(self):
        """Start the bot."""
        await self.app.start()
        logger.info("Large file handler started successfully")
    
    async def run(self):
        """Keep the bot running."""
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the bot."""
        await self.app.stop()
        logger.info("Large file handler stopped")
