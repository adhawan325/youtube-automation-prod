import os
import logging
import subprocess
from typing import Dict, List, Optional
import json
from datetime import datetime
from pathlib import Path
from gtts import gTTS
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class VideoGenerator:
    """Service for generating videos with voiceover and media assets"""
    
    def __init__(self):
        # Video generation settings
        self.output_dir = Path('media/videos')
        self.temp_dir = Path('media/temp')
        self.audio_dir = Path('media/audio')
        
        # Create directories
        for directory in [self.output_dir, self.temp_dir, self.audio_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Video settings
        self.video_settings = {
            'resolution': '1920x1080',
            'fps': 30,
            'video_codec': 'libx264',
            'audio_codec': 'aac',
            'format': 'mp4'
        }
        
        # TTS settings
        self.tts_settings = {
            'language': 'en',
            'slow': False
        }
    
    def generate_complete_video(self, script_data: Dict, media_assets: List[Dict]) -> Optional[Dict]:
        """Generate complete video with voiceover and media"""
        try:
            logger.info("Starting complete video generation")
            
            # Step 1: Generate voiceover
            logger.info("Step 1: Generating voiceover...")
            
            # Use clean script for TTS if available, otherwise clean the full script
            script_text = script_data.get('clean_script') or script_data.get('full_script', '')
            if not script_text:
                logger.error("No script content available")
                return None
            
            # If no clean script exists, clean it now
            if not script_data.get('clean_script'):
                script_text = self._clean_script_for_tts(script_text)
            
            audio_result = self.generate_voiceover_gtts(script_text)
            if not audio_result:
                logger.error("Failed to generate voiceover")
                return None
            
            # Step 2: Prepare media assets
            logger.info("Step 2: Preparing media assets...")
            audio_duration = self._get_audio_duration(audio_result['file_path'])
            prepared_assets = self._prepare_media_assets(media_assets, audio_duration)
            
            if not prepared_assets:
                logger.warning("No media assets available, creating text-only video")
            
            # Step 3: Assemble video
            logger.info("Step 3: Assembling video...")
            video_result = self._assemble_video(audio_result, prepared_assets, script_data)
            
            if not video_result:
                logger.error("Failed to assemble video")
                return None
            
            logger.info(f"Video generation completed: {video_result['file_path']}")
            return video_result
            
        except Exception as e:
            logger.error(f"Error in complete video generation: {str(e)}")
            return None
    
    def _clean_script_for_tts(self, script: str) -> str:
        """Clean script for text-to-speech by removing formatting markers"""
        import re
        
        # Remove timestamp markers like [Opening – 0:00-0:45]
        clean_script = re.sub(r'\[.*?\d+:\d+.*?\]', '', script)
        
        # Remove section headers like [Opening], [Main Content], etc.
        clean_script = re.sub(r'\[.*?\]', '', clean_script)
        
        # Remove extra whitespace and newlines
        clean_script = re.sub(r'\n+', ' ', clean_script)
        clean_script = re.sub(r'\s+', ' ', clean_script)
        
        # Clean up any remaining formatting
        clean_script = clean_script.strip()
        
        logger.info(f"Cleaned script for TTS: {len(script)} -> {len(clean_script)} characters")
        return clean_script
            
            logger.info(f"Video generation completed: {video_result['video_path']}")
            return complete_result
            
        except Exception as e:
            logger.error(f"Error in complete video generation: {str(e)}")
            return None
    
    def _generate_voiceover(self, script_data: Dict) -> Optional[Dict]:
        """Generate voiceover audio from script using gTTS"""
        try:
            full_script = script_data.get('full_script', '')
            if not full_script:
                logger.error("No script content provided")
                return None
            
            logger.info(f"Generating voiceover for script ({len(full_script)} characters)")
            
            # Use gTTS for text-to-speech
            audio_path = self._generate_gtts(full_script)
            
            if not audio_path:
                logger.error("TTS generation failed")
                return None
            
            # Get audio duration
            duration = self._get_audio_duration(audio_path)
            
            return {
                'audio_path': audio_path,
                'duration': duration,
                'script_length': len(full_script),
                'tts_method': 'gtts'
            }
            
        except Exception as e:
            logger.error(f"Error generating voiceover: {str(e)}")
            return None
    
    def _generate_gtts(self, text: str) -> Optional[str]:
        """Generate TTS using Google Text-to-Speech (gTTS)"""
        try:
            # Create audio file path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            audio_path = self.audio_dir / f"voiceover_gtts_{timestamp}.mp3"
            
            # Generate TTS
            tts = gTTS(
                text=text,
                lang=self.tts_settings.get('language', 'en'),
                slow=self.tts_settings.get('slow', False)
            )
            
            # Save audio file
            tts.save(str(audio_path))
            
            logger.info(f"gTTS generated: {audio_path}")
            return str(audio_path)
            
        except Exception as e:
            logger.error(f"gTTS error: {str(e)}")
            return None
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds"""
        try:
            audio = AudioSegment.from_file(audio_path)
            duration = len(audio) / 1000.0  # Convert milliseconds to seconds
            logger.info(f"Audio duration: {duration:.2f} seconds")
            return duration
        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return 0.0
    
    def _prepare_media_assets(self, media_assets: List[Dict], total_duration: float) -> List[Dict]:
        """Prepare media assets for video generation"""
        try:
            if not media_assets:
                logger.warning("No media assets provided")
                return []
            
            # Calculate display duration per image
            images_count = len(media_assets)
            duration_per_image = total_duration / images_count if images_count > 0 else 5.0
            
            prepared_assets = []
            for i, asset in enumerate(media_assets):
                # Try different possible file path keys
                file_path = asset.get('file_path') or asset.get('local_path') or asset.get('path')
                if not file_path or not os.path.exists(file_path):
                    logger.warning(f"Media file not found: {file_path}")
                    continue
                
                prepared_asset = {
                    'file_path': file_path,
                    'start_time': i * duration_per_image,
                    'duration': duration_per_image,
                    'attribution': asset.get('attribution', ''),
                    'type': 'image'
                }
                prepared_assets.append(prepared_asset)
            
            logger.info(f"Prepared {len(prepared_assets)} media assets")
            return prepared_assets
            
        except Exception as e:
            logger.error(f"Error preparing media assets: {str(e)}")
            return []
    
    def _assemble_video(self, audio_result: Dict, media_assets: List[Dict], 
                       script_data: Dict) -> Optional[Dict]:
        """Assemble final video using FFmpeg"""
        try:
            if not media_assets:
                logger.error("No media assets to assemble video")
                return None
            
            # Create output video path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_title = script_data.get('title', 'news_video').replace(' ', '_')[:30]
            video_path = self.output_dir / f"{video_title}_{timestamp}.mp4"
            
            # Create FFmpeg command
            ffmpeg_cmd = self._build_ffmpeg_command(
                audio_result['audio_path'],
                media_assets,
                str(video_path),
                audio_result['duration']
            )
            
            logger.info(f"Running FFmpeg command: {' '.join(ffmpeg_cmd[:5])}...")
            
            # Execute FFmpeg
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return None
            
            # Check if video file was created
            if not video_path.exists():
                logger.error("Video file was not created")
                return None
            
            # Get file size
            file_size = video_path.stat().st_size
            
            logger.info(f"Video assembled successfully: {video_path} ({file_size / 1024 / 1024:.1f} MB)")
            
            return {
                'video_path': str(video_path),
                'file_size': file_size,
                'ffmpeg_output': result.stdout
            }
            
        except Exception as e:
            logger.error(f"Error assembling video: {str(e)}")
            return None
    
    def _build_ffmpeg_command(self, audio_path: str, media_assets: List[Dict], 
                            output_path: str, total_duration: float) -> List[str]:
        """Build FFmpeg command for video assembly"""
        cmd = ['ffmpeg', '-y']  # -y to overwrite output file
        
        # Add input files with loop for images
        for asset in media_assets:
            cmd.extend(['-loop', '1', '-i', asset['file_path']])
        
        # Add audio input
        cmd.extend(['-i', audio_path])
        
        # Calculate duration per image
        duration_per_image = total_duration / len(media_assets)
        
        # Create filter complex for image slideshow with consistent sizing
        filter_parts = []
        
        # Scale and pad images to 1920x1080 with consistent SAR and timing
        for i, asset in enumerate(media_assets):
            filter_parts.append(
                f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
                f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
                f"setsar=1,fps=30[v{i}scaled]"
            )
            # Add timing for each image
            filter_parts.append(
                f"[v{i}scaled]trim=duration={duration_per_image}[v{i}]"
            )
        
        # Concatenate images with timing
        if len(media_assets) > 1:
            concat_inputs = ''.join([f"[v{i}]" for i in range(len(media_assets))])
            filter_parts.append(f"{concat_inputs}concat=n={len(media_assets)}:v=1:a=0[video]")
        else:
            filter_parts.append("[v0][video]")
        
        # Combine filter parts
        filter_complex = ';'.join(filter_parts)
        
        cmd.extend([
            '-filter_complex', filter_complex,
            '-map', '[video]',
            '-map', f'{len(media_assets)}:a',  # Audio is the last input
            '-c:v', self.video_settings['video_codec'],
            '-c:a', self.video_settings['audio_codec'],
            '-r', str(self.video_settings['fps']),
            '-t', str(total_duration),  # Set video duration to match audio
            '-pix_fmt', 'yuv420p',  # Ensure compatible pixel format
            output_path
        ])
        
        return cmd
    
    def create_thumbnail(self, video_path: str, timestamp: float = 1.0) -> Optional[str]:
        """Create thumbnail from video"""
        try:
            video_path_obj = Path(video_path)
            thumbnail_path = video_path_obj.parent / f"{video_path_obj.stem}_thumbnail.jpg"
            
            cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-ss', str(timestamp),
                '-vframes', '1',
                '-q:v', '2',
                str(thumbnail_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and thumbnail_path.exists():
                logger.info(f"Thumbnail created: {thumbnail_path}")
                return str(thumbnail_path)
            else:
                logger.error(f"Thumbnail creation failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating thumbnail: {str(e)}")
            return None

