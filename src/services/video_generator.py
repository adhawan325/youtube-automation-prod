import os
import logging
import subprocess
from datetime import datetime
from typing import Dict, List, Optional
from gtts import gTTS
import tempfile
import re

logger = logging.getLogger(__name__)

class VideoGenerator:
    """Video generation service using FFmpeg and gTTS"""
    
    def __init__(self):
        self.output_dir = os.path.join(os.getcwd(), 'media', 'videos')
        self.audio_dir = os.path.join(os.getcwd(), 'media', 'audio')
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
    
    def generate_complete_video(self, script_content: str, media_assets: List[Dict], 
                              title: str = "Generated Video") -> Dict:
        """Generate complete video with voiceover and media assets"""
        try:
            logger.info("Starting complete video generation")
            
            # Clean script for TTS
            clean_script = self._clean_script_for_tts(script_content)
            
            # Generate voiceover using gTTS
            audio_path = self._generate_voiceover_gtts(clean_script)
            if not audio_path:
                raise Exception("Failed to generate voiceover")
            
            # Get audio duration
            duration = self._get_audio_duration(audio_path)
            logger.info(f"Generated audio duration: {duration} seconds")
            
            # Extract image paths from media assets
            image_paths = []
            for asset in media_assets:
                if asset and 'file_path' in asset:
                    image_paths.append(asset['file_path'])
            
            # If no images, create a simple text-based video
            if not image_paths:
                logger.info("No images available, creating audio-only video with black background")
                image_paths = [self._create_black_background()]
            
            logger.info(f"Using {len(image_paths)} images for video")
            
            # Generate video with FFmpeg
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = re.sub(r'[^\w\s-]', '', title).strip()[:30]
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            video_filename = f"{safe_title}_{timestamp}.mp4"
            video_path = os.path.join(self.output_dir, video_filename)
            
            # Create video using FFmpeg
            success = self._create_video_with_ffmpeg(image_paths, audio_path, video_path, duration)
            
            if success and os.path.exists(video_path):
                file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
                
                result = {
                    'success': True,
                    'video_path': video_path,
                    'audio_path': audio_path,
                    'duration': duration,
                    'file_size_mb': round(file_size_mb, 2),
                    'image_count': len(image_paths),
                    'title': title,
                    'created_at': datetime.now().isoformat()
                }
                
                logger.info(f"Video generation completed: {video_path}")
                return result
            else:
                raise Exception("FFmpeg video creation failed")
                
        except Exception as e:
            logger.error(f"Error in video generation: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'created_at': datetime.now().isoformat()
            }
    
    def _clean_script_for_tts(self, script: str) -> str:
        """Clean script text for TTS by removing formatting markers"""
        if not script:
            return ""
        
        # Remove timestamp markers like [Opening – 0:00-0:45]
        clean_script = re.sub(r'\[.*?\]', '', script)
        
        # Remove section headers and formatting
        clean_script = re.sub(r'#{1,6}\s*', '', clean_script)  # Remove markdown headers
        clean_script = re.sub(r'\*{1,2}(.*?)\*{1,2}', r'\1', clean_script)  # Remove bold/italic
        clean_script = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', clean_script)  # Remove underline
        
        # Remove extra whitespace and newlines
        clean_script = re.sub(r'\n+', ' ', clean_script)
        clean_script = re.sub(r'\s+', ' ', clean_script)
        
        # Clean up any remaining formatting
        clean_script = clean_script.strip()
        
        logger.info(f"Cleaned script for TTS: {len(script)} -> {len(clean_script)} characters")
        return clean_script
    
    def _generate_voiceover_gtts(self, text: str) -> Optional[str]:
        """Generate voiceover using Google Text-to-Speech"""
        try:
            if not text or len(text.strip()) == 0:
                logger.error("No text provided for TTS")
                return None
            
            logger.info(f"Generating TTS for {len(text)} characters")
            
            # Create TTS object
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"voiceover_gtts_{timestamp}.mp3"
            audio_path = os.path.join(self.audio_dir, audio_filename)
            
            # Save audio file
            tts.save(audio_path)
            
            if os.path.exists(audio_path):
                logger.info(f"TTS audio generated: {audio_path}")
                return audio_path
            else:
                logger.error("TTS file was not created")
                return None
                
        except Exception as e:
            logger.error(f"Error generating TTS: {str(e)}")
            return None
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get audio duration using FFprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                logger.warning(f"Could not get audio duration, using default: {result.stderr}")
                return 45.0  # Default duration
        except Exception as e:
            logger.warning(f"Error getting audio duration: {str(e)}")
            return 45.0  # Default duration
    
    def _create_video_with_ffmpeg(self, image_paths: List[str], audio_path: str, 
                                 output_path: str, total_duration: float) -> bool:
        """Create video using FFmpeg with proper timing"""
        try:
            if not image_paths:
                logger.error("No image paths provided")
                return False
            
            # Calculate duration per image
            duration_per_image = total_duration / len(image_paths)
            logger.info(f"Duration per image: {duration_per_image:.2f} seconds")
            
            # Build FFmpeg command
            cmd = ['ffmpeg', '-y']  # -y to overwrite output file
            
            # Add input images with duration
            for image_path in image_paths:
                cmd.extend(['-loop', '1', '-t', str(duration_per_image), '-i', image_path])
            
            # Add audio input
            cmd.extend(['-i', audio_path])
            
            # Build filter complex for concatenation
            filter_parts = []
            for i in range(len(image_paths)):
                filter_parts.append(f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v{i}]")
            
            # Concatenate all video streams
            concat_inputs = ''.join([f"[v{i}]" for i in range(len(image_paths))])
            filter_parts.append(f"{concat_inputs}concat=n={len(image_paths)}:v=1:a=0[outv]")
            
            filter_complex = ';'.join(filter_parts)
            
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', f'{len(image_paths)}:a',  # Map audio from last input
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-pix_fmt', 'yuv420p',
                '-shortest',  # End when shortest stream ends
                output_path
            ])
            
            logger.info(f"Running FFmpeg command: {' '.join(cmd[:10])}...")
            
            # Run FFmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("FFmpeg completed successfully")
                return True
            else:
                logger.error(f"FFmpeg failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating video with FFmpeg: {str(e)}")
            return False


    
    def _create_black_background(self) -> str:
        """Create a black background image for audio-only videos"""
        try:
            import subprocess
            
            # Create black background image using FFmpeg
            bg_path = os.path.join(self.output_dir, 'black_background.png')
            
            cmd = [
                'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=black:size=1920x1080:duration=1',
                '-frames:v', '1', bg_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(bg_path):
                logger.info(f"Created black background: {bg_path}")
                return bg_path
            else:
                logger.error(f"Failed to create black background: {result.stderr}")
                # Fallback: create a simple text file as placeholder
                return "/dev/null"
                
        except Exception as e:
            logger.error(f"Error creating black background: {str(e)}")
            return "/dev/null"

