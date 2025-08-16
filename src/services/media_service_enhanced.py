import logging
import time
import traceback
import requests
from typing import List, Dict, Optional
import json
from datetime import datetime
import hashlib
from urllib.parse import urlparse
import shutil
import os
from ..utils.logger import automation_logger

logger = logging.getLogger(__name__)

class MediaService:
    """Service for discovering and managing media assets with comprehensive logging"""
    
    def __init__(self):
        self.pexels_api_key = os.getenv('PEXELS_API_KEY')
        self.unsplash_access_key = os.getenv('UNSPLASH_ACCESS_KEY')
        
        # API endpoints
        self.pexels_search_url = 'https://api.pexels.com/v1/search'
        self.pexels_video_search_url = 'https://api.pexels.com/videos/search'
        self.unsplash_search_url = 'https://api.unsplash.com/search/photos'
        
        # Local storage paths
        self.media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'media')
        self.images_dir = os.path.join(self.media_dir, 'images')
        self.videos_dir = os.path.join(self.media_dir, 'videos')
        
        # Create directories if they don't exist
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.videos_dir, exist_ok=True)
        
        automation_logger.logger.info("MediaService initialized")
        automation_logger.logger.info(f"Pexels API key configured: {'Yes' if self.pexels_api_key else 'No'}")
        automation_logger.logger.info(f"Unsplash API key configured: {'Yes' if self.unsplash_access_key else 'No'}")
        automation_logger.logger.info(f"Media directories: images={self.images_dir}, videos={self.videos_dir}")
    
    def search_images(self, query: str, limit: int = 10, orientation: str = 'landscape') -> List[Dict]:
        """Search for images using Pexels API with comprehensive logging"""
        start_time = time.time()
        
        automation_logger.logger.info(f"Starting image search for query: '{query}', limit: {limit}, orientation: {orientation}")
        
        if not self.pexels_api_key:
            automation_logger.log_api_call(
                service="Pexels",
                endpoint="search",
                error="API key not configured"
            )
            automation_logger.log_media_discovery(query, 0, "Pexels", {"error": "API key not configured"})
            logger.error("Pexels API key not configured")
            return []
        
        try:
            headers = {
                'Authorization': self.pexels_api_key
            }
            
            params = {
                'query': query,
                'per_page': limit,
                'orientation': orientation,
                'size': 'large'
            }
            
            automation_logger.log_api_call(
                service="Pexels",
                endpoint="search",
                method="GET",
                params=params
            )
            
            automation_logger.logger.debug(f"Making Pexels API request with params: {params}")
            
            response = requests.get(self.pexels_search_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            images = []
            
            automation_logger.logger.debug(f"Pexels API response: total_results={data.get('total_results')}, page={data.get('page')}, per_page={data.get('per_page')}")
            
            if 'photos' in data:
                raw_photos = data['photos']
                automation_logger.logger.info(f"Pexels returned {len(raw_photos)} photos")
                
                for i, photo in enumerate(raw_photos):
                    automation_logger.logger.debug(f"Processing photo {i+1}: id={photo.get('id')}, photographer={photo.get('photographer')}")
                    
                    processed_image = self._process_pexels_image(photo)
                    if processed_image:
                        images.append(processed_image)
                        automation_logger.logger.debug(f"Photo {i+1} processed successfully: {processed_image['url']}")
                    else:
                        automation_logger.logger.warning(f"Photo {i+1} failed processing")
            else:
                automation_logger.logger.warning(f"No 'photos' key in Pexels response: {list(data.keys())}")
            
            duration = time.time() - start_time
            
            automation_logger.log_api_call(
                service="Pexels",
                endpoint="search",
                method="GET",
                params=params,
                response_status=response.status_code,
                response_data={"images_found": len(images), "total_results": data.get('total_results')}
            )
            
            automation_logger.log_media_discovery(
                query=query,
                found_count=len(images),
                service="Pexels",
                details={"orientation": orientation, "total_available": data.get('total_results')}
            )
            
            automation_logger.log_pipeline_step(
                step_name="image_search_pexels",
                status="SUCCESS",
                details={"query": query, "images_found": len(images)},
                duration=duration
            )
            
            logger.info(f"Found {len(images)} images from Pexels in {duration:.2f}s")
            return images
            
        except Exception as e:
            duration = time.time() - start_time
            
            automation_logger.log_api_call(
                service="Pexels",
                endpoint="search",
                method="GET",
                params=params,
                error=e
            )
            
            automation_logger.log_media_discovery(
                query=query,
                found_count=0,
                service="Pexels",
                details={"error": str(e)}
            )
            
            automation_logger.log_pipeline_step(
                step_name="image_search_pexels",
                status="FAILED",
                details={"query": query, "error": str(e)},
                duration=duration
            )
            
            logger.error(f"Error searching Pexels images: {str(e)}")
            return []
    
    def search_videos(self, query: str, limit: int = 5, orientation: str = 'landscape') -> List[Dict]:
        """Search for videos using Pexels API with comprehensive logging"""
        start_time = time.time()
        
        automation_logger.logger.info(f"Starting video search for query: '{query}', limit: {limit}, orientation: {orientation}")
        
        if not self.pexels_api_key:
            automation_logger.log_api_call(
                service="Pexels Videos",
                endpoint="search",
                error="API key not configured"
            )
            automation_logger.log_media_discovery(query, 0, "Pexels Videos", {"error": "API key not configured"})
            logger.error("Pexels API key not configured for video search")
            return []
        
        try:
            headers = {
                'Authorization': self.pexels_api_key
            }
            
            params = {
                'query': query,
                'per_page': limit,
                'orientation': orientation,
                'size': 'large'
            }
            
            automation_logger.log_api_call(
                service="Pexels Videos",
                endpoint="search",
                method="GET",
                params=params
            )
            
            automation_logger.logger.debug(f"Making Pexels Videos API request with params: {params}")
            
            response = requests.get(self.pexels_video_search_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            videos = []
            
            automation_logger.logger.debug(f"Pexels Videos API response: total_results={data.get('total_results')}, page={data.get('page')}")
            
            if 'videos' in data:
                raw_videos = data['videos']
                automation_logger.logger.info(f"Pexels returned {len(raw_videos)} videos")
                
                for i, video in enumerate(raw_videos):
                    automation_logger.logger.debug(f"Processing video {i+1}: id={video.get('id')}, duration={video.get('duration')}s")
                    
                    processed_video = self._process_pexels_video(video)
                    if processed_video:
                        videos.append(processed_video)
                        automation_logger.logger.debug(f"Video {i+1} processed successfully")
                    else:
                        automation_logger.logger.warning(f"Video {i+1} failed processing")
            else:
                automation_logger.logger.warning(f"No 'videos' key in Pexels response: {list(data.keys())}")
            
            duration = time.time() - start_time
            
            automation_logger.log_api_call(
                service="Pexels Videos",
                endpoint="search",
                method="GET",
                params=params,
                response_status=response.status_code,
                response_data={"videos_found": len(videos), "total_results": data.get('total_results')}
            )
            
            automation_logger.log_media_discovery(
                query=query,
                found_count=len(videos),
                service="Pexels Videos",
                details={"orientation": orientation, "total_available": data.get('total_results')}
            )
            
            automation_logger.log_pipeline_step(
                step_name="video_search_pexels",
                status="SUCCESS",
                details={"query": query, "videos_found": len(videos)},
                duration=duration
            )
            
            logger.info(f"Found {len(videos)} videos from Pexels in {duration:.2f}s")
            return videos
            
        except Exception as e:
            duration = time.time() - start_time
            
            automation_logger.log_api_call(
                service="Pexels Videos",
                endpoint="search",
                method="GET",
                params=params,
                error=e
            )
            
            automation_logger.log_media_discovery(
                query=query,
                found_count=0,
                service="Pexels Videos",
                details={"error": str(e)}
            )
            
            automation_logger.log_pipeline_step(
                step_name="video_search_pexels",
                status="FAILED",
                details={"query": query, "error": str(e)},
                duration=duration
            )
            
            logger.error(f"Error searching Pexels videos: {str(e)}")
            return []
    
    def download_media(self, media_url: str, filename: str, media_type: str = 'image') -> Optional[str]:
        """Download media file with comprehensive logging"""
        start_time = time.time()
        
        automation_logger.logger.info(f"Starting download: {media_type} from {media_url}")
        automation_logger.logger.debug(f"Target filename: {filename}")
        
        try:
            # Determine target directory
            target_dir = self.images_dir if media_type == 'image' else self.videos_dir
            file_path = os.path.join(target_dir, filename)
            
            automation_logger.logger.debug(f"Download target path: {file_path}")
            
            # Download the file
            response = requests.get(media_url, stream=True, timeout=60)
            response.raise_for_status()
            
            file_size = int(response.headers.get('content-length', 0))
            automation_logger.logger.debug(f"Download started: content-length={file_size} bytes")
            
            with open(file_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress for large files
                        if file_size > 0 and downloaded % (1024 * 1024) == 0:  # Every MB
                            progress = (downloaded / file_size) * 100
                            automation_logger.logger.debug(f"Download progress: {progress:.1f}% ({downloaded}/{file_size} bytes)")
            
            actual_size = os.path.getsize(file_path)
            duration = time.time() - start_time
            
            automation_logger.log_pipeline_step(
                step_name=f"media_download_{media_type}",
                status="SUCCESS",
                details={
                    "url": media_url,
                    "filename": filename,
                    "file_size_bytes": actual_size,
                    "download_speed_mbps": (actual_size / (1024 * 1024)) / duration if duration > 0 else 0
                },
                duration=duration
            )
            
            automation_logger.logger.info(f"Download completed: {filename} ({actual_size} bytes) in {duration:.2f}s")
            return file_path
            
        except Exception as e:
            duration = time.time() - start_time
            
            automation_logger.log_pipeline_step(
                step_name=f"media_download_{media_type}",
                status="FAILED",
                details={"url": media_url, "filename": filename, "error": str(e)},
                duration=duration
            )
            
            automation_logger.logger.error(f"Download failed for {filename}: {str(e)}")
            return None
    
    def _process_pexels_image(self, photo: Dict) -> Optional[Dict]:
        """Process Pexels image data with logging"""
        try:
            photo_id = photo.get('id')
            photographer = photo.get('photographer', 'Unknown')
            
            # Get the best quality image URL
            src = photo.get('src', {})
            image_url = src.get('large2x') or src.get('large') or src.get('medium') or src.get('original')
            
            if not image_url:
                automation_logger.logger.warning(f"No suitable image URL found for photo {photo_id}")
                return None
            
            processed = {
                'id': photo_id,
                'url': image_url,
                'photographer': photographer,
                'photographer_url': photo.get('photographer_url'),
                'width': photo.get('width'),
                'height': photo.get('height'),
                'alt': photo.get('alt', ''),
                'source': 'Pexels',
                'attribution': f"Photo by {photographer} from Pexels"
            }
            
            automation_logger.logger.debug(f"Processed Pexels image: {photo_id} by {photographer} ({processed['width']}x{processed['height']})")
            return processed
            
        except Exception as e:
            automation_logger.logger.error(f"Error processing Pexels image: {str(e)}")
            automation_logger.logger.debug(f"Failed photo data: {photo}")
            return None
    
    def _process_pexels_video(self, video: Dict) -> Optional[Dict]:
        """Process Pexels video data with logging"""
        try:
            video_id = video.get('id')
            user = video.get('user', {})
            photographer = user.get('name', 'Unknown')
            
            # Get video files
            video_files = video.get('video_files', [])
            if not video_files:
                automation_logger.logger.warning(f"No video files found for video {video_id}")
                return None
            
            # Find the best quality video (prefer HD)
            best_video = None
            for vf in video_files:
                if vf.get('quality') == 'hd':
                    best_video = vf
                    break
            
            if not best_video:
                best_video = video_files[0]  # Fallback to first available
            
            processed = {
                'id': video_id,
                'url': best_video.get('link'),
                'quality': best_video.get('quality'),
                'width': best_video.get('width'),
                'height': best_video.get('height'),
                'duration': video.get('duration'),
                'photographer': photographer,
                'photographer_url': user.get('url'),
                'source': 'Pexels',
                'attribution': f"Video by {photographer} from Pexels"
            }
            
            automation_logger.logger.debug(f"Processed Pexels video: {video_id} by {photographer} ({processed['quality']}, {processed['duration']}s)")
            return processed
            
        except Exception as e:
            automation_logger.logger.error(f"Error processing Pexels video: {str(e)}")
            automation_logger.logger.debug(f"Failed video data: {video}")
            return None
    
    def discover_media_for_article(self, article: Dict, image_count: int = 4, video_count: int = 2) -> Dict:
        """Discover relevant media for an article with comprehensive logging"""
        start_time = time.time()
        
        title = article.get('title', '')
        content = article.get('content', '')
        keywords = article.get('keywords', [])
        
        automation_logger.logger.info(f"Starting media discovery for article: '{title[:100]}...'")
        automation_logger.logger.debug(f"Article keywords: {keywords}")
        
        # Generate search queries based on article content
        search_queries = self._generate_search_queries(title, content, keywords)
        automation_logger.logger.info(f"Generated {len(search_queries)} search queries: {search_queries}")
        
        all_images = []
        all_videos = []
        
        # Search for images
        for query in search_queries[:3]:  # Limit to top 3 queries
            automation_logger.logger.debug(f"Searching images for query: '{query}'")
            images = self.search_images(query, limit=max(2, image_count // len(search_queries[:3])))
            all_images.extend(images)
            
            if len(all_images) >= image_count:
                break
        
        # Search for videos
        for query in search_queries[:2]:  # Limit to top 2 queries for videos
            automation_logger.logger.debug(f"Searching videos for query: '{query}'")
            videos = self.search_videos(query, limit=max(1, video_count // len(search_queries[:2])))
            all_videos.extend(videos)
            
            if len(all_videos) >= video_count:
                break
        
        # Remove duplicates and limit results
        unique_images = self._remove_duplicates(all_images)[:image_count]
        unique_videos = self._remove_duplicates(all_videos)[:video_count]
        
        duration = time.time() - start_time
        
        result = {
            'images': unique_images,
            'videos': unique_videos,
            'search_queries': search_queries
        }
        
        automation_logger.log_pipeline_step(
            step_name="media_discovery_complete",
            status="SUCCESS",
            details={
                "article_title": title[:100],
                "images_found": len(unique_images),
                "videos_found": len(unique_videos),
                "search_queries": search_queries
            },
            duration=duration
        )
        
        automation_logger.logger.info(f"Media discovery completed: {len(unique_images)} images, {len(unique_videos)} videos in {duration:.2f}s")
        return result
    
    def _generate_search_queries(self, title: str, content: str, keywords: List[str]) -> List[str]:
        """Generate search queries from article content with logging"""
        queries = []
        
        # Extract key terms from title
        title_words = [word.strip('.,!?()[]{}') for word in title.lower().split() 
                      if len(word) > 3 and word not in ['the', 'and', 'for', 'with', 'from']]
        
        # Use keywords if available
        if keywords:
            queries.extend(keywords[:3])
        
        # Generate queries from title
        if len(title_words) >= 2:
            queries.append(' '.join(title_words[:2]))
        
        # Add generic geopolitical terms
        queries.extend([
            'international diplomacy',
            'government meeting',
            'political handshake',
            'conference room',
            'world map'
        ])
        
        # Remove duplicates while preserving order
        unique_queries = []
        for query in queries:
            if query not in unique_queries:
                unique_queries.append(query)
        
        automation_logger.logger.debug(f"Generated search queries from title '{title[:50]}...': {unique_queries}")
        return unique_queries[:5]  # Limit to 5 queries
    
    def _remove_duplicates(self, media_list: List[Dict]) -> List[Dict]:
        """Remove duplicate media items"""
        seen_ids = set()
        unique_media = []
        
        for item in media_list:
            item_id = item.get('id')
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                unique_media.append(item)
        
        automation_logger.logger.debug(f"Removed {len(media_list) - len(unique_media)} duplicate media items")
        return unique_media

