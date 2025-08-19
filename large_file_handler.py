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
🎬 **Welcome to Video Splitter Bot!**

I can split your videos into smaller clips. Here's how:

1️⃣ Send me a video file (up to 2GB)
2️⃣ Click the "🎬 ᴄʟɪᴘ" button or use /clip
3️⃣ Tell me how long each clip should be (in seconds)
4️⃣ I'll split your video and send you the clips!

**Features:**
✅ Support for files up to 2GB
✅ Fast processing (no re-encoding)
✅ Multiple output formats
✅ Automatic cleanup

Send me a video to get started! 🚀
        """
        
        await message.reply_text(welcome_text)
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
📹 **Video Received!**

**File Info:**
📁 Size: {file_size_mb:.1f} MB
⏱️ Duration: {duration_mins:02d}:{duration_secs:02d}
📱 Resolution: {video.width}x{video.height}

Ready to split your video! Click the button below or use /clip to continue.
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎬 ᴄʟɪᴘ", callback_data="start_clip")]
        ])
        
        await message.reply_text(response_text, reply_markup=keyboard)
        logger.info(f"Video uploaded by user {user_id}: {file_size_mb:.1f}MB, {video.duration}s")
    
    async def _handle_clip_command(self, message: Message):
        """Handle /clip command."""
        user_id = message.from_user.id
        
        if user_id not in self.user_states or "video_message" not in self.user_states[user_id]:
            await message.reply_text("❌ Please send a video first before using /clip!")
            return
        
        await self._ask_for_duration(message)
    
    async def _handle_callback(self, callback_query: CallbackQuery):
        """Handle callback queries from inline buttons."""
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if data == "start_clip":
            if user_id not in self.user_states or "video_message" not in self.user_states[user_id]:
                await callback_query.answer("❌ Please send a video first!")
                return
            
            await callback_query.answer()
            await self._ask_for_duration(callback_query.message)
    
    async def _ask_for_duration(self, message: Message):
        """Ask user for clip duration."""
        user_id = message.from_user.id if hasattr(message, 'from_user') else message.chat.id
        
        # Ensure user state exists
        if user_id not in self.user_states:
            self.user_states[user_id] = {}
        
        self.user_states[user_id]["state"] = "waiting_duration"
        
        duration_text = """
⏱️ **Clip Duration**

How long should each clip be? Send me the duration in seconds.

**Examples:**
• `30` - 30 second clips
• `60` - 1 minute clips  
• `120` - 2 minute clips
• `300` - 5 minute clips

Enter duration in seconds:
        """
        
        await message.reply_text(duration_text)
    
    async def _handle_text(self, message: Message):
        """Handle text messages (duration input)."""
        user_id = message.from_user.id
        
        if user_id not in self.user_states:
            await message.reply_text("❌ Please send a video first using /start!")
            return
        
        state = self.user_states[user_id].get("state")
        
        if state == "waiting_duration":
            try:
                duration = int(message.text.strip())
                if duration <= 0:
                    await message.reply_text("❌ Duration must be a positive number!")
                    return
                
                if duration > 3600:  # 1 hour max
                    await message.reply_text("❌ Duration too long! Maximum is 3600 seconds (1 hour).")
                    return
                
                # Start processing
                await self._process_video(message, duration)
                
            except ValueError:
                await message.reply_text("❌ Please enter a valid number for duration!")
        
        else:
            await message.reply_text("❌ I don't understand. Please send a video or use /start!")
    
    async def _process_video(self, message: Message, duration: int):
        """Process the video and split into clips."""
        user_id = message.from_user.id
        video_message = self.user_states[user_id]["video_message"]
        
        # Send processing message
        status_msg = await message.reply_text("🔄 **Processing your video...**\n\n⏳ Downloading video...")
        
        try:
            # Download video
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_path = temp_file.name
            
            await video_message.download(file_name=temp_path)
            await status_msg.edit_text("🔄 **Processing your video...**\n\n✅ Download complete\n⏳ Splitting video...")
            
            # Process video
            output_dir = f"clips/user_{user_id}"
            os.makedirs(output_dir, exist_ok=True)
            
            clip_files = await self.video_processor.split_video(
                input_path=temp_path,
                output_dir=output_dir,
                segment_duration=duration
            )
            
            await status_msg.edit_text("🔄 **Processing your video...**\n\n✅ Download complete\n✅ Video split complete\n⏳ Uploading clips...")
            
            # Upload clips
            for i, clip_path in enumerate(clip_files, 1):
                try:
                    caption = f"📹 Clip {i}/{len(clip_files)} ({duration}s each)"
                    await message.reply_video(
                        video=clip_path,
                        caption=caption
                    )
                    
                    # Update progress
                    progress = f"⏳ Uploading clips... ({i}/{len(clip_files)})"
                    await status_msg.edit_text(f"🔄 **Processing your video...**\n\n✅ Download complete\n✅ Video split complete\n{progress}")
                    
                except Exception as e:
                    logger.error(f"Failed to upload clip {i}: {e}")
                    await message.reply_text(f"❌ Failed to upload clip {i}: {str(e)}")
            
            # Success message
            await status_msg.edit_text(f"✅ **Processing Complete!**\n\n📹 {len(clip_files)} clips sent successfully!")
            
            # Cleanup
            await self._cleanup_files([temp_path] + clip_files)
            
            # Reset user state
            self.user_states[user_id] = {"state": "idle"}
            
            logger.info(f"Successfully processed video for user {user_id}: {len(clip_files)} clips")
            
        except Exception as e:
            logger.error(f"Video processing failed for user {user_id}: {e}")
            await status_msg.edit_text(f"❌ **Processing Failed!**\n\nError: {str(e)}")
            
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
