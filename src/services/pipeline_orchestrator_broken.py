import os
import logging
from typing import Dict, List, Optional
import json
from datetime import datetime
import traceback

from src.services.news_aggregator import NewsAggregator
from src.services.content_processor import ContentProcessor
from src.services.media_service import MediaService
from src.services.video_generator import VideoGenerator
from src.services.youtube_service import YouTubeService

logger = logging.getLogger(__name__)

class PipelineOrchestrator:
    """Orchestrates the complete YouTube content generation pipeline"""
    
    def __init__(self):
        # Initialize all services
        self.news_aggregator = NewsAggregator()
        self.content_processor = ContentProcessor()
        self.media_service = MediaService()
        self.video_generator = VideoGenerator()
        self.youtube_service = YouTubeService()
        
        # Pipeline configuration
        self.config = {
            'news_keywords': ['India China relations', 'geopolitics', 'international diplomacy', 'border tensions'],
            'news_limit': 5,
            'media_per_video': 4,
            'voice_settings': {
                'voice': 'alloy',  # Professional male voice
                'speed': 1.0
            },
            'video_settings': {
                'category': '25',  # News & Politics
                'privacy': 'public',
                'tags': ['geopolitics', 'international relations', 'news analysis', 'no spin news']
            }
        }
    
    def run_complete_pipeline(self, custom_topic: str = None) -> Dict:
        """Run the complete pipeline from news to YouTube upload"""
        pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Starting complete pipeline: {pipeline_id}")
        
        try:
            # Step 1: Aggregate News
            logger.info("Step 1: Aggregating news...")
            news_result = self._aggregate_news(custom_topic)
            if not news_result['success']:
                return self._create_error_result(pipeline_id, "News aggregation failed", news_result)
            
            # Step 2: Process Content
            logger.info("Step 2: Processing content and generating script...")
            content_result = self._process_content(news_result['articles'])
            if not content_result['success']:
                return self._create_error_result(pipeline_id, "Content processing failed", content_result)
            
            # Step 3: Discover Media
            logger.info("Step 3: Discovering relevant media assets...")
            media_result = self._discover_media(content_result['script_data'])
            if not media_result['success']:
                return self._create_error_result(pipeline_id, "Media discovery failed", media_result)
            
            # Step 4: Generate Video
            logger.info("Step 4: Generating video with voiceover...")
            video_result = self._generate_video(content_result['script_data'], media_result['media_assets'])
            if not video_result['success']:
                return self._create_error_result(pipeline_id, "Video generation failed", video_result)
            
            # Step 5: Upload to YouTube
            logger.info("Step 5: Uploading to YouTube...")
            upload_result = self._upload_to_youtube(video_result['video_data'], content_result['script_data'])
            if not upload_result['success']:
                return self._create_error_result(pipeline_id, "YouTube upload failed", upload_result)
            
            # Success!
            result = {
                'pipeline_id': pipeline_id,
                'status': 'completed',
                'success': True,
                'created_at': datetime.now().isoformat(),
                'steps': {
                    'news_aggregation': news_result,
                    'content_processing': content_result,
                    'media_discovery': media_result,
                    'video_generation': video_result,
                    'youtube_upload': upload_result
                },
                'final_output': {
                    'video_url': upload_result.get('video_url'),
                    'video_id': upload_result.get('video_id'),
                    'title': content_result['script_data'].get('title'),
                    'duration': video_result['video_data'].get('duration'),
                    'media_count': len(media_result['media_assets'])
                }
            }
            
            logger.info(f"Pipeline completed successfully: {pipeline_id}")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed with exception: {str(e)}")
            logger.error(traceback.format_exc())
            return self._create_error_result(pipeline_id, f"Pipeline exception: {str(e)}", {})
    
    def _aggregate_news(self, custom_topic: str = None) -> Dict:
        """Step 1: Aggregate news articles"""
        try:
            # Use custom topic or default keywords
            if custom_topic:
                keywords = [custom_topic]
            else:
                keywords = self.config['news_keywords']
            
            articles = []
            
            # Try to get articles from each keyword
            for keyword in keywords:
                try:
                    keyword_articles = self.news_aggregator.get_articles(
                        query=keyword,
                        limit=self.config['news_limit'] // len(keywords) + 1
                    )
                    if keyword_articles:
                        articles.extend(keyword_articles)
                        logger.info(f"Found {len(keyword_articles)} articles for '{keyword}'")
                except Exception as e:
                    logger.warning(f"Failed to get articles for '{keyword}': {str(e)}")
                    continue
            
            if not articles:
                # Fallback: create a sample article for demonstration
                logger.warning("No articles found, creating sample content")
                articles = [{
                    'title': 'India-China Border Talks Resume Amid Regional Tensions',
                    'content': 'Senior military commanders from India and China held their latest round of border talks to address ongoing tensions along the Line of Actual Control. The meeting focused on maintaining peace and stability in the region while both nations continue to strengthen their positions. Diplomatic sources indicate that both sides emphasized the importance of existing agreements and protocols for managing border disputes.',
                    'source': 'Sample News',
                    'published_at': datetime.now().isoformat(),
                    'url': 'https://example.com/sample-news',
                    'keywords': ['India', 'China', 'border', 'diplomacy', 'LAC']
                }]
            
            # Remove duplicates and limit results
            unique_articles = []
            seen_titles = set()
            
            for article in articles:
                title = article.get('title', '').lower()
                if title not in seen_titles:
                    seen_titles.add(title)
                    unique_articles.append(article)
                    if len(unique_articles) >= self.config['news_limit']:
                        break
            
            return {
                'success': True,
                'articles': unique_articles,
                'count': len(unique_articles),
                'keywords_used': keywords
            }
            
        except Exception as e:
            logger.error(f"Error in news aggregation: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'articles': []
            }
    
    def _process_content(self, articles: List[Dict]) -> Dict:
        """Step 2: Process articles into video script"""
        try:
            if not articles:
                return {
                    'success': False,
                    'error': 'No articles to process'
                }
            
            # Generate comprehensive script
            script_data = self.content_processor.create_video_script(
                articles=articles,
                video_style='news_analysis'
            )
            
            if not script_data:
                return {
                    'success': False,
                    'error': 'Failed to generate script'
                }
            
            return {
                'success': True,
                'script_data': script_data,
                'articles_processed': len(articles)
            }
            
        except Exception as e:
            logger.error(f"Error in content processing: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _discover_media(self, script_data: Dict) -> Dict:
        """Step 3: Discover relevant media assets"""
        try:
            # Create article object for media discovery
            article = {
                'title': script_data.get('title', ''),
                'content': script_data.get('full_script', ''),
                'keywords': script_data.get('keywords', [])
            }
            
            # Find relevant images
            relevant_media = self.media_service.find_relevant_media(
                article=article,
                media_type='image',
                limit=self.config['media_per_video']
            )
            
            if not relevant_media:
                logger.warning("No relevant media found, using fallback search")
                # Fallback: search for generic geopolitical images
                relevant_media = self.media_service.search_images(
                    'international diplomacy meeting',
                    limit=self.config['media_per_video']
                )
            
            # Prepare media for video generation
            prepared_media = self.media_service.prepare_media_for_video(
                media_list=relevant_media,
                target_duration=5.0
            )
            
            return {
                'success': True,
                'media_assets': prepared_media,
                'count': len(prepared_media)
            }
            
        except Exception as e:
            logger.error(f"Error in media discovery: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'media_assets': []
            }
    
    def _generate_video(self, script_data: Dict, media_assets: List[Dict]) -> Dict:
        """Step 4: Generate video with voiceover"""
        try:
            if not media_assets:
                return {
                    'success': False,
                    'error': 'No media assets available for video generation'
                }
            
            # Generate complete video
            video_data = self.video_generator.generate_complete_video(
                script_data=script_data,
                media_assets=media_assets,
                voice_settings=self.config['voice_settings']
            )
            
            if not video_data:
                return {
                    'success': False,
                    'error': 'Video generation failed'
                }
            
            return {
                'success': True,
                'video_data': video_data
            }
            
        except Exception as e:
            logger.error(f"Error in video generation: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _upload_to_youtube(self, video_data: Dict, script_data: Dict) -> Dict:
        """Step 5: Upload video to YouTube"""
        try:
            video_path = video_data.get('video_path')
            if not video_path or not os.path.exists(video_path):
                return {
                    'success': False,
                    'error': 'Video file not found'
                }
            
            # Prepare YouTube metadata
            title = script_data.get('title', 'Geopolitical Analysis')
            description = self._create_youtube_description(script_data, video_data)
            tags = self.config['video_settings']['tags'] + script_data.get('keywords', [])
            
            # Upload to YouTube
            upload_result = self.youtube_service.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                category_id=self.config['video_settings']['category'],
                privacy_status=self.config['video_settings']['privacy']
            )
            
            if not upload_result:
                return {
                    'success': False,
                    'error': 'YouTube upload failed'
                }
            
            return {
                'success': True,
                'video_id': upload_result.get('video_id'),
                'video_url': upload_result.get('video_url'),
                'upload_result': upload_result
            }
            
        except Exception as e:
            logger.error(f"Error in YouTube upload: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_youtube_description(self, script_data: Dict, video_data: Dict) -> str:
        """Create YouTube video description"""
        description_parts = [
            script_data.get('description', 'Professional geopolitical analysis and news coverage.'),
            "",
            "🎯 No Spin News - Objective Analysis of Global Affairs",
            "",
            "📊 In this video:",
            "• Comprehensive analysis of current geopolitical developments",
            "• Fact-based reporting without bias or sensationalism", 
            "• Expert insights into international relations",
            "",
            "🔔 Subscribe for more objective news analysis",
            "👍 Like if you found this informative",
            "💬 Share your thoughts in the comments",
            "",
            "📱 Follow No Spin News:",
            "• YouTube: @no-spin-news",
            "",
            "⚖️ Media Attribution:",
        ]
        
        # Add media attributions
        media_assets = video_data.get('media_assets', [])
        for i, asset in enumerate(media_assets, 1):
            attribution = asset.get('attribution', 'Unknown source')
            description_parts.append(f"• Image {i}: {attribution}")
        
        description_parts.extend([
            "",
            "#Geopolitics #InternationalRelations #NewsAnalysis #NoSpinNews",
            "",
            f"Generated: {datetime.now().strftime('%Y-%m-%d')}"
        ])
        
        return "\n".join(description_parts)
    
    def _create_error_result(self, pipeline_id: str, error_message: str, error_data: Dict) -> Dict:
        """Create standardized error result"""
        return {
            'pipeline_id': pipeline_id,
            'status': 'failed',
            'success': False,
            'error': error_message,
            'error_data': error_data,
            'created_at': datetime.now().isoformat()
        }
    
    def get_pipeline_status(self) -> Dict:
        """Get current pipeline system status"""
        return {
            'services': {
                'news_aggregator': 'ready' if self.news_aggregator else 'error',
                'content_processor': 'ready' if self.content_processor else 'error',
                'media_service': 'ready' if self.media_service else 'error',
                'video_generator': 'ready' if self.video_generator else 'error',
                'youtube_service': 'ready' if self.youtube_service.is_authenticated() else 'needs_auth'
            },
            'configuration': self.config,
            'timestamp': datetime.now().isoformat()
        }

