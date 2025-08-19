"""
Video Processing Engine using FFmpeg.
Handles video splitting with stream copying for fast processing.
"""

import asyncio
import logging
import os
import subprocess
from typing import List
import ffmpeg

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Handles video processing operations using FFmpeg."""
    
    def __init__(self):
        self.temp_files: List[str] = []
    
    async def split_video(self, input_path: str, output_dir: str, segment_duration: int) -> List[str]:
        """
        Split video into segments of specified duration.
        
        Args:
            input_path: Path to input video file
            output_dir: Directory to save output clips
            segment_duration: Duration of each segment in seconds
            
        Returns:
            List of paths to created clip files
        """
        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output pattern
            output_pattern = os.path.join(output_dir, "clip_%03d.mp4")
            
            logger.info(f"Splitting video: {input_path}")
            logger.info(f"Segment duration: {segment_duration}s")
            logger.info(f"Output pattern: {output_pattern}")
            
            # Build FFmpeg command using ffmpeg-python
            stream = ffmpeg.input(input_path)
            
            # Configure output with segment options
            output = ffmpeg.output(
                stream,
                output_pattern,
                format='segment',
                segment_time=segment_duration,
                c='copy',  # Stream copy - no re-encoding
                map=0,     # Map all streams
                reset_timestamps=1,
                avoid_negative_ts='make_zero',
                f='segment'
            )
            
            # Run FFmpeg command
            cmd = ffmpeg.compile(output, overwrite_output=True)
            logger.info(f"FFmpeg command: {' '.join(cmd)}")
            
            # Execute command asynchronously
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown FFmpeg error"
                logger.error(f"FFmpeg failed with return code {process.returncode}: {error_msg}")
                raise Exception(f"Video processing failed: {error_msg}")
            
            logger.info("Video splitting completed successfully")
            
            # Find all created clip files
            clip_files = []
            for filename in sorted(os.listdir(output_dir)):
                if filename.startswith("clip_") and filename.endswith(".mp4"):
                    clip_path = os.path.join(output_dir, filename)
                    if os.path.exists(clip_path) and os.path.getsize(clip_path) > 0:
                        clip_files.append(clip_path)
            
            logger.info(f"Created {len(clip_files)} clips")
            
            if not clip_files:
                raise Exception("No clips were created. The video might be shorter than the segment duration.")
            
            return clip_files
            
        except Exception as e:
            logger.error(f"Video processing error: {e}")
            raise Exception(f"Failed to process video: {str(e)}")
    
    async def get_video_info(self, video_path: str) -> dict:
        """
        Get video information using FFprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary containing video metadata
        """
        try:
            # Use ffmpeg.probe to get video information
            probe = ffmpeg.probe(video_path)
            
            # Extract video stream info
            video_stream = next(
                (stream for stream in probe['streams'] if stream['codec_type'] == 'video'),
                None
            )
            
            if not video_stream:
                raise Exception("No video stream found")
            
            # Extract useful information
            info = {
                'duration': float(probe['format']['duration']),
                'size': int(probe['format']['size']),
                'bitrate': int(probe['format']['bit_rate']),
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'fps': eval(video_stream['r_frame_rate']),  # Convert fraction to float
                'codec': video_stream['codec_name']
            }
            
            logger.info(f"Video info extracted: {info}")
            return info
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise Exception(f"Could not analyze video: {str(e)}")
    
    async def estimate_clip_count(self, video_path: str, segment_duration: int) -> int:
        """
        Estimate how many clips will be created.
        
        Args:
            video_path: Path to video file
            segment_duration: Duration of each segment in seconds
            
        Returns:
            Estimated number of clips
        """
        try:
            info = await self.get_video_info(video_path)
            duration = info['duration']
            clip_count = int(duration / segment_duration) + (1 if duration % segment_duration > 0 else 0)
            
            logger.info(f"Estimated clips: {clip_count} (duration: {duration}s, segment: {segment_duration}s)")
            return clip_count
            
        except Exception as e:
            logger.error(f"Failed to estimate clip count: {e}")
            return 0
    
    def cleanup_temp_files(self):
        """Clean up any temporary files created during processing."""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        
        self.temp_files.clear()
    
    async def validate_video_file(self, video_path: str) -> bool:
        """
        Validate that the file is a valid video.
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if valid video, False otherwise
        """
        try:
            # Try to probe the file
            await self.get_video_info(video_path)
            return True
        except:
            return False
