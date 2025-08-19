# Telegram Video Splitter Bot

## Overview

A Telegram bot that splits video files into smaller segments of user-specified durations. The bot supports two operational modes: a standard mode for files up to 20MB using the Telegram Bot API, and an enhanced mode for files up to 2GB using the MTProto protocol via Pyrogram. The system uses FFmpeg for efficient video processing with stream copying to maintain quality while minimizing processing time.

## User Preferences

Preferred communication style: Simple, everyday language.
Deployment preference: Hardcoded credentials in source code for easy deployment across different Replit accounts without setup.

## System Architecture

### Dual Bot Architecture
The application implements a dual-mode architecture to handle different file size requirements:

**Primary Mode (Large Files)**: Uses MTProto protocol via Pyrogram client to support files up to 2GB. This mode requires Telegram API credentials (API_ID and API_HASH) and provides enhanced file handling capabilities.

**Fallback Mode (Standard Files)**: Uses the standard Telegram Bot API with a 20MB file size limit. This mode serves as a backup when MTProto credentials are unavailable or when the primary mode fails.

### Entry Points Strategy
Two separate entry points (`main_large.py` and `main.py`) allow for flexible deployment. The large file handler is attempted first, with automatic fallback to the standard bot if initialization fails.

### Video Processing Pipeline
The system implements a multi-stage processing pipeline:
1. **File Reception**: Bot receives video files through Telegram
2. **Download Management**: Files are downloaded to temporary storage
3. **FFmpeg Processing**: Videos are split using FFmpeg with stream copying for performance
4. **Clip Generation**: Segments are created based on user-specified duration
5. **Upload and Delivery**: Individual clips are sent back to the user
6. **Cleanup**: Temporary files are removed to manage storage

### State Management
User sessions are tracked using in-memory dictionaries that store:
- Current user state (waiting for video, waiting for duration, etc.)
- Video file information and metadata
- Processing status and temporary file paths

### User Interface Design
The bot implements an interactive workflow using:
- Inline keyboards for clip creation commands
- Callback query handling for button interactions
- Command-based navigation (/start, /clip)
- Progressive user guidance through the splitting process

## External Dependencies

### Core Libraries
- **python-telegram-bot**: Standard Telegram Bot API integration for the fallback mode
- **pyrogram**: MTProto protocol client for large file support (up to 2GB)
- **tgcrypto**: Encryption library required by Pyrogram for secure communication
- **ffmpeg-python**: Python wrapper for FFmpeg command execution

### System Dependencies
- **FFmpeg**: Video processing engine for splitting operations, configured with full codec support
- **Python 3.11**: Runtime environment

### Telegram Services
- **Telegram Bot API**: Standard bot functionality and file handling up to 20MB
- **Telegram MTProto API**: Enhanced protocol for large file transfers and advanced bot features

### File System Requirements
- Temporary storage for video downloads and processing
- Output directory structure for generated clips
- Automatic cleanup mechanisms for storage management