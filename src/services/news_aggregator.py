import requests
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)

class NewsAggregator:
    """Service for aggregating news from various sources"""
    
    def __init__(self):
        self.newsapi_ai_key = os.getenv('NEWSAPI_AI_KEY')
        self.newsapi_org_key = os.getenv('NEWSAPI_ORG_KEY')
        self.base_url_ai = 'https://newsapi.ai/api/v1/article/getArticles'
        self.base_url_org = 'https://newsapi.org/v2/everything'
    
    def get_articles(self, query: str, limit: int = 10) -> List[Dict]:
        """Get articles for a specific query - main interface method"""
        return self.aggregate_news(keywords=[query], limit=limit)
        
    def search_newsapi_ai(self, keywords: List[str], limit: int = 10, 
                         days_back: int = 1) -> List[Dict]:
        """Search for articles using NewsAPI.ai"""
        if not self.newsapi_ai_key:
            logger.warning("NewsAPI.ai key not configured")
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
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
            
            response = requests.post(self.base_url_ai, json=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if 'articles' in data and 'results' in data['articles']:
                for article in data['articles']['results']:
                    processed_article = self._process_newsapi_ai_article(article)
                    if processed_article:
                        articles.append(processed_article)
            
            logger.info(f"Retrieved {len(articles)} articles from NewsAPI.ai")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI.ai: {str(e)}")
            return []
    
    def search_newsapi_org(self, keywords: List[str], limit: int = 10,
                          days_back: int = 1) -> List[Dict]:
        """Search for articles using NewsAPI.org (fallback)"""
        if not self.newsapi_org_key:
            logger.warning("NewsAPI.org key not configured")
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Prepare query
            query = ' OR '.join(keywords)
            
            params = {
                'apiKey': self.newsapi_org_key,
                'q': query,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'sortBy': 'publishedAt',
                'pageSize': limit,
                'language': 'en'
            }
            
            response = requests.get(self.base_url_org, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if 'articles' in data:
                for article in data['articles']:
                    processed_article = self._process_newsapi_org_article(article)
                    if processed_article:
                        articles.append(processed_article)
            
            logger.info(f"Retrieved {len(articles)} articles from NewsAPI.org")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI.org: {str(e)}")
            return []
    
    def _process_newsapi_ai_article(self, article: Dict) -> Optional[Dict]:
        """Process article from NewsAPI.ai format"""
        try:
            # Extract basic information
            title = article.get('title', '').strip()
            body = article.get('body', '').strip()
            url = article.get('url', '')
            
            if not title or not body or not url:
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
            else:
                published_at = datetime.now()
            
            # Extract categories and concepts
            categories = []
            if 'categories' in article:
                categories = [cat.get('label', '') for cat in article['categories']]
            
            concepts = []
            if 'concepts' in article:
                concepts = [concept.get('label', '') for concept in article['concepts']]
            
            # Extract sentiment
            sentiment = 'neutral'
            if 'sentiment' in article:
                sentiment = article['sentiment'].get('label', 'neutral').lower()
            
            # Extract image
            image_url = None
            if 'image' in article:
                image_url = article['image']
            
            return {
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
                'relevance_score': self._calculate_relevance_score(title, body, concepts)
            }
            
        except Exception as e:
            logger.error(f"Error processing NewsAPI.ai article: {str(e)}")
            return None
    
    def _process_newsapi_org_article(self, article: Dict) -> Optional[Dict]:
        """Process article from NewsAPI.org format"""
        try:
            title = article.get('title', '').strip()
            description = article.get('description', '').strip()
            content = article.get('content', '').strip()
            url = article.get('url', '')
            
            if not title or not url:
                return None
            
            # Use description as content if full content not available
            body = content if content else description
            if not body:
                return None
            
            # Parse published date
            published_at = article.get('publishedAt')
            if published_at:
                try:
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    published_at = datetime.now()
            else:
                published_at = datetime.now()
            
            # Extract source
            source_info = article.get('source', {})
            source_name = source_info.get('name', 'Unknown Source')
            
            return {
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
                'relevance_score': self._calculate_relevance_score(title, body, [])
            }
            
        except Exception as e:
            logger.error(f"Error processing NewsAPI.org article: {str(e)}")
            return None
    
    def _calculate_relevance_score(self, title: str, content: str, 
                                 concepts: List[str]) -> float:
        """Calculate relevance score for an article"""
        score = 0.0
        
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
            elif keyword in content_lower:
                score += 1.0
        
        # Score based on concepts (if available)
        for concept in concepts:
            concept_lower = concept.lower()
            for keyword in important_keywords:
                if keyword in concept_lower:
                    score += 1.5
        
        # Normalize score (0-10 scale)
        return min(score, 10.0)
    
    def aggregate_news(self, keywords: List[str] = None, limit: int = 10,
                      days_back: int = 1) -> List[Dict]:
        """Aggregate news from all available sources"""
        if keywords is None:
            keywords = [
                'India geopolitics', 'China India relations', 'Pakistan India',
                'Modi international', 'South Asia politics', 'Kashmir',
                'BRICS', 'international relations', 'diplomacy'
            ]
        
        all_articles = []
        
        # Try NewsAPI.ai first (preferred)
        articles_ai = self.search_newsapi_ai(keywords, limit, days_back)
        all_articles.extend(articles_ai)
        
        # If we don't have enough articles, try NewsAPI.org
        if len(all_articles) < limit:
            remaining = limit - len(all_articles)
            articles_org = self.search_newsapi_org(keywords, remaining, days_back)
            all_articles.extend(articles_org)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
        
        # Sort by relevance score and published date
        unique_articles.sort(
            key=lambda x: (x['relevance_score'], x['published_at']),
            reverse=True
        )
        
        logger.info(f"Aggregated {len(unique_articles)} unique articles")
        return unique_articles[:limit]
    
    def get_trending_topics(self, days_back: int = 7) -> List[str]:
        """Get trending topics based on recent articles"""
        # This would analyze recent articles to identify trending topics
        # For now, return default topics relevant to the channel
        return [
            'India China border',
            'Modi foreign policy',
            'Pakistan relations',
            'BRICS summit',
            'Kashmir situation',
            'Trade agreements',
            'Defense cooperation',
            'Diplomatic meetings'
        ]
        
    def search_newsapi_ai(self, keywords: List[str], limit: int = 10, 
                         days_back: int = 1) -> List[Dict]:
        """Search for articles using NewsAPI.ai"""
        if not self.newsapi_ai_key:
            logger.warning("NewsAPI.ai key not configured")
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
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
            
            response = requests.post(self.base_url_ai, json=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if 'articles' in data and 'results' in data['articles']:
                for article in data['articles']['results']:
                    processed_article = self._process_newsapi_ai_article(article)
                    if processed_article:
                        articles.append(processed_article)
            
            logger.info(f"Retrieved {len(articles)} articles from NewsAPI.ai")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI.ai: {str(e)}")
            return []
    
    def search_newsapi_org(self, keywords: List[str], limit: int = 10,
                          days_back: int = 1) -> List[Dict]:
        """Search for articles using NewsAPI.org (fallback)"""
        if not self.newsapi_org_key:
            logger.warning("NewsAPI.org key not configured")
            return []
        
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Prepare query
            query = ' OR '.join(keywords)
            
            params = {
                'apiKey': self.newsapi_org_key,
                'q': query,
                'from': start_date.strftime('%Y-%m-%d'),
                'to': end_date.strftime('%Y-%m-%d'),
                'sortBy': 'publishedAt',
                'pageSize': limit,
                'language': 'en'
            }
            
            response = requests.get(self.base_url_org, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            articles = []
            
            if 'articles' in data:
                for article in data['articles']:
                    processed_article = self._process_newsapi_org_article(article)
                    if processed_article:
                        articles.append(processed_article)
            
            logger.info(f"Retrieved {len(articles)} articles from NewsAPI.org")
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI.org: {str(e)}")
            return []
    
    def _process_newsapi_ai_article(self, article: Dict) -> Optional[Dict]:
        """Process article from NewsAPI.ai format"""
        try:
            # Extract basic information
            title = article.get('title', '').strip()
            body = article.get('body', '').strip()
            url = article.get('url', '')
            
            if not title or not body or not url:
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
            else:
                published_at = datetime.now()
            
            # Extract categories and concepts
            categories = []
            if 'categories' in article:
                categories = [cat.get('label', '') for cat in article['categories']]
            
            concepts = []
            if 'concepts' in article:
                concepts = [concept.get('label', '') for concept in article['concepts']]
            
            # Extract sentiment
            sentiment = 'neutral'
            if 'sentiment' in article:
                sentiment = article['sentiment'].get('label', 'neutral').lower()
            
            # Extract image
            image_url = None
            if 'image' in article:
                image_url = article['image']
            
            return {
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
                'relevance_score': self._calculate_relevance_score(title, body, concepts)
            }
            
        except Exception as e:
            logger.error(f"Error processing NewsAPI.ai article: {str(e)}")
            return None
    
    def _process_newsapi_org_article(self, article: Dict) -> Optional[Dict]:
        """Process article from NewsAPI.org format"""
        try:
            title = article.get('title', '').strip()
            description = article.get('description', '').strip()
            content = article.get('content', '').strip()
            url = article.get('url', '')
            
            if not title or not url:
                return None
            
            # Use description as content if full content not available
            body = content if content else description
            if not body:
                return None
            
            # Parse published date
            published_at = article.get('publishedAt')
            if published_at:
                try:
                    published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    published_at = datetime.now()
            else:
                published_at = datetime.now()
            
            # Extract source
            source_info = article.get('source', {})
            source_name = source_info.get('name', 'Unknown Source')
            
            return {
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
                'relevance_score': self._calculate_relevance_score(title, body, [])
            }
            
        except Exception as e:
            logger.error(f"Error processing NewsAPI.org article: {str(e)}")
            return None
    
    def _calculate_relevance_score(self, title: str, content: str, 
                                 concepts: List[str]) -> float:
        """Calculate relevance score for an article"""
        score = 0.0
        
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
            elif keyword in content_lower:
                score += 1.0
        
        # Score based on concepts (if available)
        for concept in concepts:
            concept_lower = concept.lower()
            for keyword in important_keywords:
                if keyword in concept_lower:
                    score += 1.5
        
        # Normalize score (0-10 scale)
        return min(score, 10.0)
    
    def aggregate_news(self, keywords: List[str] = None, limit: int = 10,
                      days_back: int = 1) -> List[Dict]:
        """Aggregate news from all available sources"""
        if keywords is None:
            keywords = [
                'India geopolitics', 'China India relations', 'Pakistan India',
                'Modi international', 'South Asia politics', 'Kashmir',
                'BRICS', 'international relations', 'diplomacy'
            ]
        
        all_articles = []
        
        # Try NewsAPI.ai first (preferred)
        articles_ai = self.search_newsapi_ai(keywords, limit, days_back)
        all_articles.extend(articles_ai)
        
        # If we don't have enough articles, try NewsAPI.org
        if len(all_articles) < limit:
            remaining = limit - len(all_articles)
            articles_org = self.search_newsapi_org(keywords, remaining, days_back)
            all_articles.extend(articles_org)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
        
        # Sort by relevance score and published date
        unique_articles.sort(
            key=lambda x: (x['relevance_score'], x['published_at']),
            reverse=True
        )
        
        logger.info(f"Aggregated {len(unique_articles)} unique articles")
        return unique_articles[:limit]
    
    def get_trending_topics(self, days_back: int = 7) -> List[str]:
        """Get trending topics based on recent articles"""
        # This would analyze recent articles to identify trending topics
        # For now, return default topics relevant to the channel
        return [
            'India China border',
            'Modi foreign policy',
            'Pakistan relations',
            'BRICS summit',
            'Kashmir situation',
            'Trade agreements',
            'Defense cooperation',
            'Diplomatic meetings'
        ]

