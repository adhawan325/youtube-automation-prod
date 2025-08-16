import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import time
import requests
from ..utils.logger import automation_logger

logger = logging.getLogger(__name__)

class NewsAggregator:
    """Service for aggregating news from various sources with comprehensive logging"""
    
    def __init__(self):
        self.newsapi_ai_key = os.getenv('NEWSAPI_AI_KEY')
        self.newsapi_org_key = os.getenv('NEWSAPI_ORG_KEY')
        self.base_url_ai = 'https://newsapi.ai/api/v1/article/getArticles'
        self.base_url_org = 'https://newsapi.org/v2/everything'
        
        automation_logger.logger.info("NewsAggregator initialized")
        automation_logger.logger.info(f"NewsAPI.ai key configured: {'Yes' if self.newsapi_ai_key else 'No'}")
        automation_logger.logger.info(f"NewsAPI.org key configured: {'Yes' if self.newsapi_org_key else 'No'}")
    
    def get_articles(self, query: str, limit: int = 10) -> List[Dict]:
        """Get articles for a specific query - main interface method"""
        automation_logger.logger.info(f"Getting articles for query: '{query}', limit: {limit}")
        return self.aggregate_news(keywords=[query], limit=limit)
        
    def search_newsapi_ai(self, keywords: List[str], limit: int = 10, 
                         days_back: int = 1) -> List[Dict]:
        """Search for articles using NewsAPI.ai with comprehensive logging"""
        start_time = time.time()
        
        if not self.newsapi_ai_key:
            automation_logger.log_api_call(
                service="NewsAPI.ai",
                endpoint="getArticles",
                error="API key not configured"
            )
            logger.warning("NewsAPI.ai key not configured")
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            automation_logger.logger.info(f"Searching NewsAPI.ai for keywords: {keywords}, date range: {start_date.date()} to {end_date.date()}")
            
            # Prepare query parameters
            params = {
                'apiKey': self.newsapi_ai_key,
                'query': {
                    '$query': {
                        '$and': [
                            {
                                '$or': [
                                    {'title': keyword} for keyword in keywords
                                ] + [
                                    {'body': keyword} for keyword in keywords
                                ]
                            },
                            {
                                'dateStart': start_date.strftime('%Y-%m-%d'),
                                'dateEnd': end_date.strftime('%Y-%m-%d')
                            }
                        ]
                    }
                },
                'articlesPage': 1,
                'articlesCount': limit,
                'articlesSortBy': 'date',
                'includeArticleTitle': True,
                'includeArticleBody': True,
                'includeArticleUrl': True,
                'includeArticleImage': True,
                'includeSourceTitle': True,
                'includeSourceDescription': True,
                'includeArticleCategories': True,
                'includeArticleConcepts': True,
                'includeArticleSentiment': True
            }
            
            automation_logger.log_api_call(
                service="NewsAPI.ai",
                endpoint="getArticles",
                method="POST",
                params={"keywords": keywords, "limit": limit, "days_back": days_back}
            )
            
            response = requests.post(self.base_url_ai, json=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            automation_logger.logger.debug(f"NewsAPI.ai response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if 'articles' in data and 'results' in data['articles']:
                raw_articles = data['articles']['results']
                automation_logger.logger.info(f"NewsAPI.ai returned {len(raw_articles)} raw articles")
                
                for i, article in enumerate(raw_articles):
                    automation_logger.logger.debug(f"Processing article {i+1}: {article.get('title', 'No title')[:100]}...")
                    processed_article = self._process_newsapi_ai_article(article)
                    if processed_article:
                        articles.append(processed_article)
                        automation_logger.logger.debug(f"Article {i+1} processed successfully, relevance score: {processed_article.get('relevance_score', 0)}")
                    else:
                        automation_logger.logger.warning(f"Article {i+1} failed processing")
            else:
                automation_logger.logger.warning(f"Unexpected NewsAPI.ai response structure: {data}")
            
            duration = time.time() - start_time
            
            automation_logger.log_api_call(
                service="NewsAPI.ai",
                endpoint="getArticles",
                method="POST",
                params={"keywords": keywords, "limit": limit},
                response_status=response.status_code,
                response_data={"articles_found": len(articles), "raw_articles": len(data.get('articles', {}).get('results', []))}
            )
            
            automation_logger.log_pipeline_step(
                step_name="news_aggregation_newsapi_ai",
                status="SUCCESS",
                details={"articles_found": len(articles), "keywords": keywords},
                duration=duration
            )
            
            logger.info(f"Retrieved {len(articles)} articles from NewsAPI.ai in {duration:.2f}s")
            return articles
            
        except Exception as e:
            duration = time.time() - start_time
            automation_logger.log_api_call(
                service="NewsAPI.ai",
                endpoint="getArticles",
                method="POST",
                params={"keywords": keywords, "limit": limit},
                error=e
            )
            
            automation_logger.log_pipeline_step(
                step_name="news_aggregation_newsapi_ai",
                status="FAILED",
                details={"error": str(e), "keywords": keywords},
                duration=duration
            )
            
            logger.error(f"Error fetching from NewsAPI.ai: {str(e)}")
            return []
    
    def search_newsapi_org(self, keywords: List[str], limit: int = 10,
                          days_back: int = 1) -> List[Dict]:
        """Search for articles using NewsAPI.org (fallback) with logging"""
        start_time = time.time()
        
        if not self.newsapi_org_key:
            automation_logger.log_api_call(
                service="NewsAPI.org",
                endpoint="everything",
                error="API key not configured"
            )
            logger.warning("NewsAPI.org key not configured")
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Prepare query
            query = ' OR '.join(keywords)
            automation_logger.logger.info(f"Searching NewsAPI.org with query: '{query}', date range: {start_date.date()} to {end_date.date()}")
            
            params = {
                'apiKey': self.newsapi_org_key,
                'q': query,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'sortBy': 'publishedAt',
                'pageSize': limit,
                'language': 'en'
            }
            
            automation_logger.log_api_call(
                service="NewsAPI.org",
                endpoint="everything",
                method="GET",
                params={"query": query, "limit": limit, "days_back": days_back}
            )
            
            response = requests.get(self.base_url_org, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            automation_logger.logger.debug(f"NewsAPI.org response: status={data.get('status')}, totalResults={data.get('totalResults')}")
            
            if 'articles' in data:
                raw_articles = data['articles']
                automation_logger.logger.info(f"NewsAPI.org returned {len(raw_articles)} raw articles")
                
                for i, article in enumerate(raw_articles):
                    automation_logger.logger.debug(f"Processing article {i+1}: {article.get('title', 'No title')[:100]}...")
                    processed_article = self._process_newsapi_org_article(article)
                    if processed_article:
                        articles.append(processed_article)
                        automation_logger.logger.debug(f"Article {i+1} processed successfully")
                    else:
                        automation_logger.logger.warning(f"Article {i+1} failed processing")
            
            duration = time.time() - start_time
            
            automation_logger.log_api_call(
                service="NewsAPI.org",
                endpoint="everything",
                method="GET",
                params={"query": query, "limit": limit},
                response_status=response.status_code,
                response_data={"articles_found": len(articles), "total_results": data.get('totalResults')}
            )
            
            automation_logger.log_pipeline_step(
                step_name="news_aggregation_newsapi_org",
                status="SUCCESS",
                details={"articles_found": len(articles), "query": query},
                duration=duration
            )
            
            logger.info(f"Retrieved {len(articles)} articles from NewsAPI.org in {duration:.2f}s")
            return articles
            
        except Exception as e:
            duration = time.time() - start_time
            automation_logger.log_api_call(
                service="NewsAPI.org",
                endpoint="everything",
                method="GET",
                params={"query": query, "limit": limit},
                error=e
            )
            
            automation_logger.log_pipeline_step(
                step_name="news_aggregation_newsapi_org",
                status="FAILED",
                details={"error": str(e), "query": query},
                duration=duration
            )
            
            logger.error(f"Error fetching from NewsAPI.org: {str(e)}")
            return []
    
    def _process_newsapi_ai_article(self, article: Dict) -> Optional[Dict]:
        """Process article from NewsAPI.ai format with detailed logging"""
        try:
            # Extract basic information
            title = article.get('title', '').strip()
            body = article.get('body', '').strip()
            url = article.get('url', '')
            
            automation_logger.logger.debug(f"Processing article: title_length={len(title)}, body_length={len(body)}, has_url={bool(url)}")
            
            if not title or not body or not url:
                automation_logger.logger.warning(f"Article missing required fields: title={bool(title)}, body={bool(body)}, url={bool(url)}")
                return None
            
            # Extract source information
            source_info = article.get('source', {})
            source_title = source_info.get('title', 'Unknown Source')
            
            # Extract metadata
            published_at = article.get('dateTime')
            if published_at:
                try:
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    published_at = datetime.now()
                    automation_logger.logger.warning(f"Failed to parse date: {article.get('dateTime')}")
            else:
                published_at = datetime.now()
            
            # Extract categories and concepts
            categories = []
            if 'categories' in article:
                categories = [cat.get('label', '') for cat in article['categories']]
                automation_logger.logger.debug(f"Article categories: {categories}")
            
            concepts = []
            if 'concepts' in article:
                concepts = [concept.get('label', '') for concept in article['concepts']]
                automation_logger.logger.debug(f"Article concepts: {concepts[:5]}...")  # Log first 5 concepts
            
            # Extract sentiment
            sentiment = 'neutral'
            if 'sentiment' in article:
                sentiment = article['sentiment'].get('label', 'neutral').lower()
                automation_logger.logger.debug(f"Article sentiment: {sentiment}")
            
            # Extract image
            image_url = None
            if 'image' in article:
                image_url = article['image']
                automation_logger.logger.debug(f"Article has image: {bool(image_url)}")
            
            relevance_score = self._calculate_relevance_score(title, body, concepts)
            automation_logger.logger.debug(f"Calculated relevance score: {relevance_score}")
            
            processed = {
                'title': title,
                'content': body,
                'url': url,
                'source': source_title,
                'author': article.get('authors', [{}])[0].get('name') if article.get('authors') else None,
                'published_at': published_at,
                'keywords': concepts,
                'categories': categories,
                'sentiment': sentiment,
                'image_url': image_url,
                'relevance_score': relevance_score
            }
            
            automation_logger.logger.debug(f"Successfully processed article: {title[:50]}...")
            return processed
            
        except Exception as e:
            automation_logger.logger.error(f"Error processing NewsAPI.ai article: {str(e)}")
            automation_logger.logger.debug(f"Failed article data: {article}")
            return None
    
    def _process_newsapi_org_article(self, article: Dict) -> Optional[Dict]:
        """Process article from NewsAPI.org format with detailed logging"""
        try:
            title = article.get('title', '').strip()
            description = article.get('description', '').strip()
            content = article.get('content', '').strip()
            url = article.get('url', '')
            
            automation_logger.logger.debug(f"Processing NewsAPI.org article: title_length={len(title)}, desc_length={len(description)}, content_length={len(content)}")
            
            if not title or not url:
                automation_logger.logger.warning(f"NewsAPI.org article missing required fields: title={bool(title)}, url={bool(url)}")
                return None
            
            # Use description as content if full content not available
            body = content if content else description
            if not body:
                automation_logger.logger.warning("NewsAPI.org article has no content or description")
                return None
            
            # Parse published date
            published_at = article.get('publishedAt')
            if published_at:
                try:
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    published_at = datetime.now()
                    automation_logger.logger.warning(f"Failed to parse NewsAPI.org date: {article.get('publishedAt')}")
            else:
                published_at = datetime.now()
            
            # Extract source
            source_info = article.get('source', {})
            source_name = source_info.get('name', 'Unknown Source')
            
            relevance_score = self._calculate_relevance_score(title, body, [])
            automation_logger.logger.debug(f"NewsAPI.org article relevance score: {relevance_score}")
            
            processed = {
                'title': title,
                'content': body,
                'url': url,
                'source': source_name,
                'author': article.get('author'),
                'published_at': published_at,
                'keywords': [],  # NewsAPI.org doesn't provide keywords
                'categories': [],
                'sentiment': 'neutral',  # NewsAPI.org doesn't provide sentiment
                'image_url': article.get('urlToImage'),
                'relevance_score': relevance_score
            }
            
            automation_logger.logger.debug(f"Successfully processed NewsAPI.org article: {title[:50]}...")
            return processed
            
        except Exception as e:
            automation_logger.logger.error(f"Error processing NewsAPI.org article: {str(e)}")
            automation_logger.logger.debug(f"Failed NewsAPI.org article data: {article}")
            return None
    
    def _calculate_relevance_score(self, title: str, content: str, 
                                 concepts: List[str]) -> float:
        """Calculate relevance score for an article with detailed logging"""
        score = 0.0
        matches = []
        
        # Keywords that are important for the channel
        important_keywords = [
            'india', 'china', 'pakistan', 'geopolitics', 'international',
            'modi', 'diplomacy', 'trade', 'security', 'policy', 'government',
            'kashmir', 'border', 'relations', 'summit', 'agreement', 'conflict'
        ]
        
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Score based on title keywords
        for keyword in important_keywords:
            if keyword in title_lower:
                score += 2.0  # Title matches are more important
                matches.append(f"title:{keyword}")
            elif keyword in content_lower:
                score += 1.0
                matches.append(f"content:{keyword}")
        
        # Score based on concepts (if available)
        for concept in concepts:
            concept_lower = concept.lower()
            for keyword in important_keywords:
                if keyword in concept_lower:
                    score += 1.5
                    matches.append(f"concept:{keyword}")
        
        # Normalize score (0-10 scale)
        final_score = min(score, 10.0)
        
        automation_logger.logger.debug(f"Relevance calculation: matches={matches}, raw_score={score}, final_score={final_score}")
        
        return final_score
    
    def aggregate_news(self, keywords: List[str] = None, limit: int = 10,
                      days_back: int = 1) -> List[Dict]:
        """Aggregate news from all available sources with comprehensive logging"""
        start_time = time.time()
        
        if keywords is None:
            keywords = [
                'India geopolitics', 'China India relations', 'Pakistan India',
                'Modi international', 'South Asia politics', 'Kashmir',
                'BRICS', 'international relations', 'diplomacy'
            ]
        
        # Force recent news only - use shorter time window for fresher content
        days_back = min(days_back, 2)  # Maximum 2 days back for latest news
        
        automation_logger.logger.info(f"Starting news aggregation with {len(keywords)} keyword groups, limit={limit}, days_back={days_back} (forced recent)")
        automation_logger.logger.debug(f"Keywords: {keywords}")
        
        all_articles = []
        
        # Try NewsAPI.ai first (preferred)
        automation_logger.logger.info("Attempting NewsAPI.ai search...")
        articles_ai = self.search_newsapi_ai(keywords, limit, days_back)
        all_articles.extend(articles_ai)
        automation_logger.logger.info(f"NewsAPI.ai contributed {len(articles_ai)} articles")
        
        # If we don't have enough articles, try NewsAPI.org
        if len(all_articles) < limit:
            remaining = limit - len(all_articles)
            automation_logger.logger.info(f"Need {remaining} more articles, trying NewsAPI.org...")
            articles_org = self.search_newsapi_org(keywords, remaining, days_back)
            all_articles.extend(articles_org)
            automation_logger.logger.info(f"NewsAPI.org contributed {len(articles_org)} articles")
        
        # Filter out articles older than 3 days regardless of API response
        cutoff_date = datetime.now() - timedelta(days=3)
        recent_articles = []
        old_articles_filtered = 0
        
        for article in all_articles:
            if article['published_at'] >= cutoff_date:
                recent_articles.append(article)
            else:
                old_articles_filtered += 1
                automation_logger.logger.debug(f"Filtered old article: {article['title'][:50]}... (published: {article['published_at'].date()})")
        
        automation_logger.logger.info(f"Filtered out {old_articles_filtered} articles older than 3 days")
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        duplicates_removed = 0
        
        for article in recent_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
            else:
                duplicates_removed += 1
        
        automation_logger.logger.info(f"Removed {duplicates_removed} duplicate articles")
        
        # Sort by published date first (newest first), then by relevance score
        unique_articles.sort(
            key=lambda x: (x['published_at'], x['relevance_score']),
            reverse=True
        )
        
        # Log top articles with dates
        for i, article in enumerate(unique_articles[:5]):
            automation_logger.logger.debug(f"Top article {i+1}: published={article['published_at'].strftime('%Y-%m-%d %H:%M')}, score={article['relevance_score']}, title={article['title'][:100]}...")
        
        final_articles = unique_articles[:limit]
        duration = time.time() - start_time
        
        automation_logger.log_pipeline_step(
            step_name="news_aggregation_complete",
            status="SUCCESS",
            details={
                "total_articles": len(final_articles),
                "sources_used": ["NewsAPI.ai", "NewsAPI.org"],
                "duplicates_removed": duplicates_removed,
                "old_articles_filtered": old_articles_filtered,
                "keywords": keywords
            },
            duration=duration
        )
        
        logger.info(f"Aggregated {len(final_articles)} unique articles in {duration:.2f}s")
        return final_articles
    
    def get_trending_topics(self, days_back: int = 7) -> List[str]:
        """Get trending topics based on recent articles"""
        automation_logger.logger.info(f"Getting trending topics for last {days_back} days")
        
        # This would analyze recent articles to identify trending topics
        # For now, return default topics relevant to the channel
        topics = [
            'India China border',
            'Modi foreign policy',
            'Pakistan relations',
            'BRICS summit',
            'Kashmir situation',
            'Trade agreements',
            'Defense cooperation',
            'Diplomatic meetings'
        ]
        
        automation_logger.logger.debug(f"Returning {len(topics)} trending topics")
        return topics

