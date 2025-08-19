"""
Standard Telegram Bot Handler using python-telegram-bot.
Supports files up to 20MB using standard Bot API.
"""

import asyncio
import logging
import os
import tempfile
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from video_processor import VideoProcessor

logger = logging.getLogger(__name__)

class TelegramVideoBot:
    """Standard Telegram bot with 20MB file limit."""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.user_states: Dict[int, Dict[str, Any]] = {}
        self.video_processor = VideoProcessor()
        
        # Initialize application
        self.application = Application.builder().token(self.bot_token).build()
        self._register_handlers()
    
    def _register_handlers(self):
        """Register all command and message handlers."""
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("clip", self._handle_clip_command))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.VIDEO, self._handle_video))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(self._handle_callback))
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = """
🎬 **Welcome to Video Splitter Bot!**

I can split your videos into smaller clips. Here's how:

1️⃣ Send me a video file (up to 20MB)
2️⃣ Click the "🎬 ᴄʟɪᴘ" button or use /clip
3️⃣ Tell me how long each clip should be (in seconds)
4️⃣ I'll split your video and send you the clips!

**Features:**
✅ Support for files up to 20MB
✅ Fast processing (no re-encoding)
✅ Multiple output formats
✅ Automatic cleanup

Send me a video to get started! 🚀

**Note:** This is the standard mode. For files larger than 20MB, please use the large file version.
        """
        
        await update.message.reply_text(welcome_text)
        logger.info(f"User {update.effective_user.id} started the bot")
    
    async def _handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video uploads."""
        user_id = update.effective_user.id
        video = update.message.video
        
        # Check file size (20MB limit for standard bot)
        max_size = 20 * 1024 * 1024  # 20MB in bytes
        if video.file_size > max_size:
            await update.message.reply_text(
                f"❌ **File too large!**\n\n"
                f"Your file: {video.file_size / (1024*1024):.1f} MB\n"
                f"Maximum allowed: 20 MB\n\n"
                f"Please use a smaller file or contact the developer for large file support."
            )
            return
        
        # Store video information
        self.user_states[user_id] = {
            "video_message": update.message,
            "state": "video_uploaded"
        }
        
        # Get video info
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
        
        await update.message.reply_text(response_text, reply_markup=keyboard)
        logger.info(f"Video uploaded by user {user_id}: {file_size_mb:.1f}MB, {video.duration}s")
    
    async def _handle_clip_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clip command."""
        user_id = update.effective_user.id
        
        if user_id not in self.user_states or "video_message" not in self.user_states[user_id]:
            await update.message.reply_text("❌ Please send a video first before using /clip!")
            return
        
        await self._ask_for_duration(update.message)
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline buttons."""
        query = update.callback_query
        user_id = update.effective_user.id
        data = query.data
        
        if data == "start_clip":
            if user_id not in self.user_states or "video_message" not in self.user_states[user_id]:
                await query.answer("❌ Please send a video first!")
                return
            
            await query.answer()
            await self._ask_for_duration(query.message)
    
    async def _ask_for_duration(self, message):
        """Ask user for clip duration."""
        user_id = message.chat.id
        
        if user_id in self.user_states:
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
    
    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (duration input)."""
        user_id = update.effective_user.id
        
        if user_id not in self.user_states:
            await update.message.reply_text("❌ Please send a video first using /start!")
            return
        
        state = self.user_states[user_id].get("state")
        
        if state == "waiting_duration":
            try:
                duration = int(update.message.text.strip())
                if duration <= 0:
                    await update.message.reply_text("❌ Duration must be a positive number!")
                    return
                
                if duration > 3600:  # 1 hour max
                    await update.message.reply_text("❌ Duration too long! Maximum is 3600 seconds (1 hour).")
                    return
                
                # Start processing
                await self._process_video(update, duration)
                
            except ValueError:
                await update.message.reply_text("❌ Please enter a valid number for duration!")
        
        else:
            await update.message.reply_text("❌ I don't understand. Please send a video or use /start!")
    
    async def _process_video(self, update: Update, duration: int):
        """Process the video and split into clips."""
        user_id = update.effective_user.id
        video_message = self.user_states[user_id]["video_message"]
        
        # Send processing message
        status_msg = await update.message.reply_text("🔄 **Processing your video...**\n\n⏳ Downloading video...")
        
        try:
            # Download video
            file = await video_message.video.get_file()
            
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                temp_path = temp_file.name
            
            await file.download_to_drive(temp_path)
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
                    with open(clip_path, 'rb') as clip_file:
                        await update.message.reply_video(
                            video=clip_file,
                            caption=caption
                        )
                    
                    # Update progress
                    progress = f"⏳ Uploading clips... ({i}/{len(clip_files)})"
                    await status_msg.edit_text(f"🔄 **Processing your video...**\n\n✅ Download complete\n✅ Video split complete\n{progress}")
                    
                except Exception as e:
                    logger.error(f"Failed to upload clip {i}: {e}")
                    await update.message.reply_text(f"❌ Failed to upload clip {i}: {str(e)}")
            
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
                if 'temp_path' in locals():
                    await self._cleanup_files([temp_path])
            except:
                pass
    
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
        logger.info("Starting standard bot...")
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Standard bot started successfully")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        finally:
            await self.application.stop()
