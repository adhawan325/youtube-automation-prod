import requests
import os
import logging
from typing import List, Dict, Optional
import json
from datetime import datetime
import hashlib
from urllib.parse import urlparse
import shutil

logger = logging.getLogger(__name__)

class MediaService:
    """Service for discovering and managing media assets from various sources"""
    
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
    
    def search_images(self, query: str, limit: int = 10, orientation: str = 'landscape') -> List[Dict]:
        """Search for images using Pexels API"""
        if not self.pexels_api_key:
            logger.warning("Pexels API key not configured")
            return []
        
        try:
            headers = {
                'Authorization': self.pexels_api_key
            }
            
            params = {
                'query': query,
                'per_page': limit,
                'orientation': orientation,  # landscape, portrait, square
                'size': 'large'  # large, medium, small
            }
            
            response = requests.get(self.pexels_search_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            images = []
            
            if 'photos' in data:
                for photo in data['photos']:
                    processed_image = self._process_pexels_image(photo)
                    if processed_image:
                        images.append(processed_image)
            
            logger.info(f"Found {len(images)} images for query: {query}")
            return images
            
        except Exception as e:
            logger.error(f"Error searching Pexels images: {str(e)}")
            return []
    
    def search_videos(self, query: str, limit: int = 5, orientation: str = 'landscape') -> List[Dict]:
        """Search for videos using Pexels API"""
        if not self.pexels_api_key:
            logger.warning("Pexels API key not configured")
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
            
            response = requests.get(self.pexels_video_search_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            videos = []
            
            if 'videos' in data:
                for video in data['videos']:
                    processed_video = self._process_pexels_video(video)
                    if processed_video:
                        videos.append(processed_video)
            
            logger.info(f"Found {len(videos)} videos for query: {query}")
            return videos
            
        except Exception as e:
            logger.error(f"Error searching Pexels videos: {str(e)}")
            return []
    
    def _process_pexels_image(self, photo: Dict) -> Optional[Dict]:
        """Process image data from Pexels API response"""
        try:
            # Get the best quality image URL
            src = photo.get('src', {})
            image_url = src.get('large2x') or src.get('large') or src.get('medium')
            
            if not image_url:
                return None
            
            return {
                'id': photo.get('id'),
                'url': image_url,
                'photographer': photo.get('photographer'),
                'photographer_url': photo.get('photographer_url'),
                'width': photo.get('width'),
                'height': photo.get('height'),
                'alt': photo.get('alt', ''),
                'source': 'pexels',
                'media_type': 'image',
                'license_type': 'pexels_free',
                'attribution_required': True,
                'attribution_text': f"Photo by {photo.get('photographer')} from Pexels",
                'pexels_url': photo.get('url')
            }
            
        except Exception as e:
            logger.error(f"Error processing Pexels image: {str(e)}")
            return None
    
    def _process_pexels_video(self, video: Dict) -> Optional[Dict]:
        """Process video data from Pexels API response"""
        try:
            # Get the best quality video URL
            video_files = video.get('video_files', [])
            if not video_files:
                return None
            
            # Sort by quality (prefer HD)
            video_files.sort(key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
            best_video = video_files[0]
            
            return {
                'id': video.get('id'),
                'url': best_video.get('link'),
                'photographer': video.get('user', {}).get('name'),
                'photographer_url': video.get('user', {}).get('url'),
                'width': best_video.get('width'),
                'height': best_video.get('height'),
                'duration': video.get('duration'),
                'source': 'pexels',
                'media_type': 'video',
                'license_type': 'pexels_free',
                'attribution_required': True,
                'attribution_text': f"Video by {video.get('user', {}).get('name')} from Pexels",
                'pexels_url': video.get('url'),
                'file_type': best_video.get('file_type', 'mp4')
            }
            
        except Exception as e:
            logger.error(f"Error processing Pexels video: {str(e)}")
            return None
    
    def download_media(self, media_item: Dict) -> Optional[str]:
        """Download media file to local storage"""
        try:
            media_url = media_item.get('url')
            if not media_url:
                logger.error("No URL provided for media download")
                return None
            
            # Generate filename
            media_id = media_item.get('id', 'unknown')
            media_type = media_item.get('media_type', 'image')
            source = media_item.get('source', 'unknown')
            
            # Get file extension from URL
            parsed_url = urlparse(media_url)
            file_ext = os.path.splitext(parsed_url.path)[1]
            if not file_ext:
                file_ext = '.jpg' if media_type == 'image' else '.mp4'
            
            filename = f"{source}_{media_id}_{hashlib.md5(media_url.encode()).hexdigest()[:8]}{file_ext}"
            
            # Determine storage directory
            if media_type == 'image':
                local_path = os.path.join(self.images_dir, filename)
            else:
                local_path = os.path.join(self.videos_dir, filename)
            
            # Check if file already exists
            if os.path.exists(local_path):
                logger.info(f"Media file already exists: {filename}")
                return local_path
            
            # Download the file
            logger.info(f"Downloading {media_type} from {source}: {filename}")
            
            response = requests.get(media_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            
            logger.info(f"Successfully downloaded: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}")
            return None
    
    def find_relevant_media(self, article: Dict, media_type: str = 'image', limit: int = 5) -> List[Dict]:
        """Find relevant media for an article"""
        try:
            title = article.get('title', '')
            content = article.get('content', '')
            keywords = article.get('keywords', [])
            
            # Generate search queries based on article content
            search_queries = self._generate_search_queries(title, content, keywords)
            
            all_media = []
            
            for query in search_queries[:3]:  # Limit to top 3 queries
                if media_type == 'image':
                    media_results = self.search_images(query, limit=limit//len(search_queries[:3]) + 1)
                else:
                    media_results = self.search_videos(query, limit=limit//len(search_queries[:3]) + 1)
                
                all_media.extend(media_results)
                
                # Break if we have enough results
                if len(all_media) >= limit:
                    break
            
            # Remove duplicates and limit results
            seen_ids = set()
            unique_media = []
            for media in all_media:
                media_id = media.get('id')
                if media_id and media_id not in seen_ids:
                    seen_ids.add(media_id)
                    unique_media.append(media)
                    if len(unique_media) >= limit:
                        break
            
            # Score and sort by relevance
            scored_media = []
            for media in unique_media:
                relevance_score = self._calculate_media_relevance(media, title, content, keywords)
                media['relevance_score'] = relevance_score
                scored_media.append(media)
            
            # Sort by relevance score
            scored_media.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            logger.info(f"Found {len(scored_media)} relevant {media_type}s for article: {title[:50]}...")
            return scored_media
            
        except Exception as e:
            logger.error(f"Error finding relevant media: {str(e)}")
            return []
    
    def _generate_search_queries(self, title: str, content: str, keywords: List[str]) -> List[str]:
        """Generate search queries based on article content"""
        queries = []
        
        # Use keywords if available
        if keywords:
            for keyword in keywords[:5]:  # Top 5 keywords
                queries.append(keyword)
        
        # Extract key terms from title
        title_words = title.lower().split()
        important_words = []
        
        # Filter for important words (countries, leaders, concepts)
        geopolitical_terms = [
            'india', 'china', 'pakistan', 'modi', 'xi', 'imran', 'kashmir',
            'border', 'diplomacy', 'trade', 'summit', 'meeting', 'agreement',
            'conflict', 'relations', 'policy', 'defense', 'security'
        ]
        
        for word in title_words:
            if word in geopolitical_terms or len(word) > 6:  # Long words are often important
                important_words.append(word)
        
        # Create queries from important words
        if important_words:
            queries.extend(important_words[:3])
        
        # Generic fallback queries for geopolitical content
        if not queries:
            queries = [
                'international relations',
                'diplomacy meeting',
                'government officials',
                'world leaders',
                'political discussion'
            ]
        
        return queries[:5]  # Limit to 5 queries
    
    def _calculate_media_relevance(self, media: Dict, title: str, content: str, keywords: List[str]) -> float:
        """Calculate relevance score for media item"""
        score = 0.0
        
        alt_text = media.get('alt', '').lower()
        photographer = media.get('photographer', '').lower()
        
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Score based on alt text matching
        for keyword in keywords:
            if keyword.lower() in alt_text:
                score += 2.0
        
        # Score based on title words in alt text
        title_words = title_lower.split()
        for word in title_words:
            if len(word) > 4 and word in alt_text:
                score += 1.0
        
        # Bonus for professional/news-related content
        professional_terms = [
            'business', 'meeting', 'conference', 'official', 'government',
            'leader', 'politician', 'diplomat', 'handshake', 'flag',
            'building', 'office', 'suit', 'formal'
        ]
        
        for term in professional_terms:
            if term in alt_text:
                score += 1.5
        
        # Penalty for irrelevant content
        irrelevant_terms = [
            'party', 'celebration', 'wedding', 'food', 'animal',
            'sport', 'game', 'entertainment', 'music', 'art'
        ]
        
        for term in irrelevant_terms:
            if term in alt_text:
                score -= 1.0
        
        return max(score, 0.0)  # Ensure non-negative score
    
    def get_media_attribution(self, media: Dict) -> str:
        """Get proper attribution text for media"""
        attribution = media.get('attribution_text', '')
        
        if not attribution:
            source = media.get('source', 'Unknown')
            photographer = media.get('photographer', 'Unknown')
            
            if source == 'pexels':
                attribution = f"Photo by {photographer} from Pexels"
            elif source == 'unsplash':
                attribution = f"Photo by {photographer} on Unsplash"
            else:
                attribution = f"Photo by {photographer}"
        
        return attribution
    
    def prepare_media_for_video(self, media_list: List[Dict], target_duration: float = 5.0) -> List[Dict]:
        """Prepare media assets for video generation"""
        prepared_media = []
        
        for media in media_list:
            # Download media if not already downloaded
            local_path = self.download_media(media)
            if not local_path:
                continue
            
            media_info = {
                'local_path': local_path,
                'media_type': media.get('media_type'),
                'duration': target_duration,  # How long to show this media in video
                'attribution': self.get_media_attribution(media),
                'width': media.get('width'),
                'height': media.get('height'),
                'source': media.get('source'),
                'relevance_score': media.get('relevance_score', 0)
            }
            
            prepared_media.append(media_info)
        
        return prepared_media
    
    def cleanup_old_media(self, days_old: int = 7) -> int:
        """Clean up old downloaded media files"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days_old * 24 * 3600)
            
            cleaned_count = 0
            
            for directory in [self.images_dir, self.videos_dir]:
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        file_time = os.path.getmtime(file_path)
                        if file_time < cutoff_time:
                            os.remove(file_path)
                            cleaned_count += 1
                            logger.info(f"Cleaned up old media file: {filename}")
            
            logger.info(f"Cleaned up {cleaned_count} old media files")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up old media: {str(e)}")
            return 0

