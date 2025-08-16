import openai
import logging
from typing import Dict, List, Optional
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class ContentProcessor:
    """Service for processing and summarizing news content"""
    
    def __init__(self):
        # Set up OpenAI client
        openai.api_key = os.getenv('OPENAI_API_KEY')
        openai.api_base = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
        
        # Channel-specific settings
        self.channel_style = {
            'tone': 'objective and analytical',
            'approach': 'no spin, fact-based reporting',
            'focus': 'geopolitical implications and context',
            'target_audience': 'informed viewers interested in international relations'
        }
    
    def summarize_article(self, article: Dict, target_length: str = 'medium') -> Dict:
        """Summarize a single article for video script"""
        try:
            title = article.get('title', '')
            content = article.get('content', '')
            
            if not content:
                logger.warning(f"No content available for article: {title}")
                return None
            
            # Determine target word count based on length
            word_counts = {
                'short': '100-150 words',
                'medium': '200-300 words', 
                'long': '400-500 words'
            }
            target_words = word_counts.get(target_length, '200-300 words')
            
            # Create summarization prompt
            prompt = self._create_summarization_prompt(
                title, content, target_words
            )
            
            # Call OpenAI API
            response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Extract components from the response
            components = self._parse_summary_response(summary)
            
            return {
                'original_title': title,
                'summary_title': components.get('title', title),
                'hook': components.get('hook', ''),
                'context': components.get('context', ''),
                'main_points': components.get('main_points', []),
                'implications': components.get('implications', ''),
                'conclusion': components.get('conclusion', ''),
                'full_script': components.get('full_script', summary),
                'word_count': len(summary.split()),
                'estimated_duration': self._estimate_duration(summary),
                'keywords': self._extract_keywords(summary),
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error summarizing article: {str(e)}")
            return None
    
    def create_video_script(self, articles: List[Dict], video_style: str = "professional") -> Dict:
        """Create comprehensive video script from articles"""
        try:
            logger.info(f"Creating video script from {len(articles)} articles")
            
            # Summarize articles first
            article_summaries = []
            for article in articles:
                summary = self.summarize_article(article, target_length='short')
                if summary:
                    article_summaries.append({
                        'title': article.get('title', ''),
                        'summary': summary,
                        'source': article.get('source', ''),
                        'published_at': article.get('published_at', '')
                    })
            
            if not article_summaries:
                logger.warning("No article summaries available")
                return None
            
            # Create comprehensive script
            script_prompt = self._create_script_prompt(article_summaries, video_style)
            
            response = openai.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": self._get_script_system_prompt()},
                    {"role": "user", "content": script_prompt}
                ],
                max_tokens=1500,
                temperature=0.4
            )
            
            script_content = response.choices[0].message.content.strip()
            script_components = self._parse_script_response(script_content)
            
            # Clean the script for TTS (remove timestamp markers and formatting)
            clean_script = self._clean_script_for_tts(script_components.get('full_script', ''))
            script_components['clean_script'] = clean_script
            
            logger.info("Video script created successfully")
            return script_components
            
        except Exception as e:
            logger.error(f"Error creating video script: {str(e)}")
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
        
        logger.info(f"Cleaned script: {len(script)} -> {len(clean_script)} characters")
        return clean_script
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for article summarization"""
        return f"""You are a professional news analyst for the "No Spin News" YouTube channel. 
        
        Channel characteristics:
        - Tone: {self.channel_style['tone']}
        - Approach: {self.channel_style['approach']}
        - Focus: {self.channel_style['focus']}
        - Audience: {self.channel_style['target_audience']}
        
        Your task is to create engaging, informative summaries that provide context and analysis 
        without bias or sensationalism. Focus on facts, implications, and broader significance.
        
        Structure your response with clear sections:
        - TITLE: Engaging but factual title
        - HOOK: Opening statement to capture attention
        - CONTEXT: Background information needed to understand the story
        - MAIN_POINTS: Key facts and developments
        - IMPLICATIONS: What this means for the region/world
        - CONCLUSION: Wrap-up and key takeaway
        """
    
    def _get_script_system_prompt(self) -> str:
        """Get system prompt for video script creation"""
        return f"""You are creating a complete video script for the "No Spin News" YouTube channel.
        
        Channel style:
        - {self.channel_style['approach']}
        - {self.channel_style['tone']}
        - Focus on {self.channel_style['focus']}
        - Target audience: {self.channel_style['target_audience']}
        
        Create a cohesive narrative that connects multiple news stories, providing context and analysis.
        The script should be suitable for voiceover narration and include natural transitions between topics.
        
        Structure:
        - TITLE: Compelling video title
        - DESCRIPTION: YouTube description with key points
        - FULL_SCRIPT: Complete narration script
        - SEGMENTS: Break down into timed segments
        - TAGS: Relevant YouTube tags
        """
    
    def _create_summarization_prompt(self, title: str, content: str, 
                                   target_words: str) -> str:
        """Create prompt for article summarization"""
        return f"""Please analyze and summarize this news article for a YouTube video script.
        
        Article Title: {title}
        
        Article Content: {content}
        
        Requirements:
        - Target length: {target_words}
        - Maintain objectivity and factual accuracy
        - Provide necessary context for viewers
        - Focus on geopolitical implications if relevant
        - Use clear, engaging language suitable for narration
        - Structure with the sections specified in the system prompt
        
        Please provide a comprehensive summary that would work well as part of a news analysis video."""
    
    def _create_script_prompt(self, summaries: List[Dict], style: str) -> str:
        """Create prompt for video script generation"""
        articles_text = "\n\n".join([
            f"Article {i+1}: {summary.get('title', 'Untitled')}\n{summary.get('summary', {}).get('full_script', str(summary.get('summary', '')))}"
            for i, summary in enumerate(summaries)
        ])
        
        return f"""Create a complete video script using these summarized articles:
        
        {articles_text}
        
        Video Style: {style}
        
        Requirements:
        - Create a cohesive narrative connecting these stories
        - Include smooth transitions between topics
        - Maintain the "No Spin News" objective approach
        - Target duration: 5-8 minutes
        - Include engaging opening and strong conclusion
        - Provide context for viewers who may not be familiar with ongoing situations
        - Focus on implications and broader significance
        
        Please structure the response with all the sections specified in the system prompt."""
    
    def _parse_summary_response(self, response: str) -> Dict:
        """Parse the structured response from OpenAI"""
        components = {}
        
        # Extract sections using regex
        sections = {
            'title': r'TITLE:\s*(.*?)(?=\n|$)',
            'hook': r'HOOK:\s*(.*?)(?=\n\n|\n[A-Z]+:|$)',
            'context': r'CONTEXT:\s*(.*?)(?=\n\n|\n[A-Z]+:|$)',
            'main_points': r'MAIN_POINTS:\s*(.*?)(?=\n\n|\n[A-Z]+:|$)',
            'implications': r'IMPLICATIONS:\s*(.*?)(?=\n\n|\n[A-Z]+:|$)',
            'conclusion': r'CONCLUSION:\s*(.*?)(?=\n\n|\n[A-Z]+:|$)'
        }
        
        for key, pattern in sections.items():
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                components[key] = match.group(1).strip()
        
        # If structured parsing fails, use the full response
        if not components:
            components['full_script'] = response
        else:
            # Combine all sections into full script
            script_parts = []
            for key in ['hook', 'context', 'main_points', 'implications', 'conclusion']:
                if key in components and components[key]:
                    script_parts.append(components[key])
            components['full_script'] = '\n\n'.join(script_parts)
        
        return components
    
    def _parse_script_response(self, response: str) -> Dict:
        """Parse the structured script response"""
        components = {}
        
        sections = {
            'title': r'TITLE:\s*(.*?)(?=\n|$)',
            'description': r'DESCRIPTION:\s*(.*?)(?=\n\n|\n[A-Z]+:|$)',
            'full_script': r'FULL_SCRIPT:\s*(.*?)(?=\n\n|\n[A-Z]+:|$)',
            'tags': r'TAGS:\s*(.*?)(?=\n\n|\n[A-Z]+:|$)'
        }
        
        for key, pattern in sections.items():
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if key == 'tags':
                    # Parse tags as list
                    components[key] = [tag.strip() for tag in content.split(',')]
                else:
                    components[key] = content
        
        # If no structured content found, use full response as script
        if 'full_script' not in components:
            components['full_script'] = response
        
        return components
    
    def _estimate_duration(self, text: str) -> float:
        """Estimate video duration based on text length"""
        # Average speaking rate: 150-160 words per minute
        # Using 150 WPM for conservative estimate
        word_count = len(text.split())
        duration_minutes = word_count / 150
        return round(duration_minutes, 1)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text"""
        # Simple keyword extraction - could be enhanced with NLP
        common_keywords = [
            'India', 'China', 'Pakistan', 'Modi', 'geopolitics',
            'international', 'diplomacy', 'trade', 'security',
            'Kashmir', 'border', 'relations', 'policy', 'government'
        ]
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in common_keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def generate_title_variations(self, base_title: str, count: int = 5) -> List[str]:
        """Generate multiple title variations for A/B testing"""
        try:
            prompt = f"""Generate {count} different YouTube video title variations for this base title: "{base_title}"
            
            Requirements:
            - Maintain factual accuracy
            - Make them engaging but not clickbait
            - Suitable for "No Spin News" channel
            - Focus on geopolitical angle if relevant
            - Keep under 60 characters when possible
            
            Return only the titles, one per line."""
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            titles = response.choices[0].message.content.strip().split('\n')
            return [title.strip() for title in titles if title.strip()]
            
        except Exception as e:
            logger.error(f"Error generating title variations: {str(e)}")
            return [base_title]
    
    def optimize_for_seo(self, script_data: Dict) -> Dict:
        """Optimize content for YouTube SEO"""
        try:
            title = script_data.get('title', '')
            description = script_data.get('description', '')
            
            # Generate SEO-optimized description
            seo_prompt = f"""Optimize this YouTube video description for SEO:
            
            Title: {title}
            Current Description: {description}
            
            Requirements:
            - Include relevant keywords naturally
            - Add timestamps if applicable
            - Include call-to-action
            - Mention key topics covered
            - Keep under 1000 characters
            - Maintain professional tone
            
            Return the optimized description."""
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": seo_prompt}
                ],
                max_tokens=400,
                temperature=0.3
            )
            
            optimized_description = response.choices[0].message.content.strip()
            
            # Update script data
            script_data['seo_description'] = optimized_description
            script_data['seo_optimized'] = True
            
            return script_data
            
        except Exception as e:
            logger.error(f"Error optimizing for SEO: {str(e)}")
            return script_data

