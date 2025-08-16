import os
import logging
from typing import Dict, Optional, List
import json
from datetime import datetime
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger(__name__)

class YouTubeService:
    """Service for uploading videos to YouTube and managing channel operations"""
    
    # YouTube API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/youtube.upload',
        'https://www.googleapis.com/auth/youtube',
        'https://www.googleapis.com/auth/youtube.readonly'
    ]
    
    def __init__(self):
        self.credentials_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'google_credentials.json')
        self.token_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'youtube_token.pickle')
        self.youtube_service = None
        self.credentials = None
        
        # Initialize the service
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize the YouTube API service with authentication"""
        try:
            self.credentials = self._get_credentials()
            if self.credentials:
                self.youtube_service = build('youtube', 'v3', credentials=self.credentials)
                logger.info("YouTube service initialized successfully")
            else:
                logger.warning("YouTube service not initialized - credentials required")
        except Exception as e:
            logger.error(f"Error initializing YouTube service: {str(e)}")
    
    def _get_credentials(self) -> Optional[Credentials]:
        """Get or refresh YouTube API credentials"""
        creds = None
        
        # Load existing token if available
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("Loaded existing YouTube credentials")
            except Exception as e:
                logger.warning(f"Error loading existing credentials: {str(e)}")
        
        # If there are no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed YouTube credentials")
                except Exception as e:
                    logger.warning(f"Error refreshing credentials: {str(e)}")
                    creds = None
            
            if not creds:
                # Check if credentials file exists
                if not os.path.exists(self.credentials_file):
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    return None
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, self.SCOPES
                    )
                    # Use localhost for the callback
                    creds = flow.run_local_server(port=8080, open_browser=False)
                    logger.info("Obtained new YouTube credentials")
                except Exception as e:
                    logger.error(f"Error obtaining new credentials: {str(e)}")
                    return None
            
            # Save the credentials for future use
            if creds:
                try:
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(creds, token)
                    logger.info("Saved YouTube credentials")
                except Exception as e:
                    logger.warning(f"Error saving credentials: {str(e)}")
        
        return creds
    
    def get_auth_url(self) -> Optional[str]:
        """Get authorization URL for manual OAuth flow"""
        try:
            if not os.path.exists(self.credentials_file):
                logger.error(f"Credentials file not found: {self.credentials_file}")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_file, self.SCOPES
            )
            flow.redirect_uri = 'http://localhost:5000/oauth2callback'
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Error generating auth URL: {str(e)}")
            return None
    
    def upload_video(self, video_path: str, title: str, description: str = '', 
                    tags: List[str] = None, category_id: str = '25', 
                    privacy_status: str = 'public') -> Optional[Dict]:
        """Upload a video to YouTube"""
        if not self.youtube_service:
            logger.error("YouTube service not initialized")
            return None
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None
        
        try:
            # Prepare video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags or [],
                    'categoryId': category_id,
                    'defaultLanguage': 'en',
                    'defaultAudioLanguage': 'en'
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Create media upload object
            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/*'
            )
            
            logger.info(f"Starting upload for video: {title}")
            
            # Execute the upload
            insert_request = self.youtube_service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            response = self._resumable_upload(insert_request)
            
            if response:
                video_id = response.get('id')
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                logger.info(f"Video uploaded successfully: {video_url}")
                
                return {
                    'video_id': video_id,
                    'video_url': video_url,
                    'title': title,
                    'status': 'uploaded',
                    'privacy_status': privacy_status,
                    'upload_time': datetime.now().isoformat()
                }
            else:
                logger.error("Upload failed - no response received")
                return None
                
        except HttpError as e:
            logger.error(f"HTTP error during upload: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            return None
    
    def _resumable_upload(self, insert_request):
        """Handle resumable upload with retry logic"""
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        logger.info(f"Upload completed. Video ID: {response['id']}")
                    else:
                        logger.error(f"Upload failed with unexpected response: {response}")
                        return None
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    # Retriable HTTP errors
                    error = f"Retriable HTTP error {e.resp.status}: {e.content}"
                    logger.warning(error)
                else:
                    # Non-retriable HTTP error
                    logger.error(f"Non-retriable HTTP error: {str(e)}")
                    return None
            except Exception as e:
                error = f"Unexpected error: {str(e)}"
                logger.error(error)
                return None
            
            if error is not None:
                retry += 1
                if retry > 3:
                    logger.error("Maximum retries exceeded")
                    return None
                
                max_sleep = 2 ** retry
                import time
                import random
                sleep_seconds = random.random() * max_sleep
                logger.info(f"Sleeping {sleep_seconds} seconds and then retrying...")
                time.sleep(sleep_seconds)
        
        return response
    
    def get_channel_info(self) -> Optional[Dict]:
        """Get information about the authenticated channel"""
        if not self.youtube_service:
            logger.error("YouTube service not initialized")
            return None
        
        try:
            request = self.youtube_service.channels().list(
                part='snippet,statistics,contentDetails',
                mine=True
            )
            response = request.execute()
            
            if 'items' in response and len(response['items']) > 0:
                channel = response['items'][0]
                
                return {
                    'channel_id': channel['id'],
                    'title': channel['snippet']['title'],
                    'description': channel['snippet']['description'],
                    'subscriber_count': channel['statistics'].get('subscriberCount', 0),
                    'video_count': channel['statistics'].get('videoCount', 0),
                    'view_count': channel['statistics'].get('viewCount', 0),
                    'thumbnail_url': channel['snippet']['thumbnails']['default']['url']
                }
            else:
                logger.warning("No channel information found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting channel info: {str(e)}")
            return None
    
    def get_video_analytics(self, video_id: str) -> Optional[Dict]:
        """Get analytics for a specific video"""
        if not self.youtube_service:
            logger.error("YouTube service not initialized")
            return None
        
        try:
            request = self.youtube_service.videos().list(
                part='statistics,snippet',
                id=video_id
            )
            response = request.execute()
            
            if 'items' in response and len(response['items']) > 0:
                video = response['items'][0]
                
                return {
                    'video_id': video_id,
                    'title': video['snippet']['title'],
                    'view_count': video['statistics'].get('viewCount', 0),
                    'like_count': video['statistics'].get('likeCount', 0),
                    'comment_count': video['statistics'].get('commentCount', 0),
                    'published_at': video['snippet']['publishedAt']
                }
            else:
                logger.warning(f"No video found with ID: {video_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting video analytics: {str(e)}")
            return None
    
    def update_video_metadata(self, video_id: str, title: str = None, 
                            description: str = None, tags: List[str] = None) -> bool:
        """Update metadata for an existing video"""
        if not self.youtube_service:
            logger.error("YouTube service not initialized")
            return False
        
        try:
            # Get current video details
            request = self.youtube_service.videos().list(
                part='snippet',
                id=video_id
            )
            response = request.execute()
            
            if not response['items']:
                logger.error(f"Video not found: {video_id}")
                return False
            
            video = response['items'][0]
            snippet = video['snippet']
            
            # Update only provided fields
            if title:
                snippet['title'] = title
            if description:
                snippet['description'] = description
            if tags:
                snippet['tags'] = tags
            
            # Update the video
            update_request = self.youtube_service.videos().update(
                part='snippet',
                body={
                    'id': video_id,
                    'snippet': snippet
                }
            )
            update_request.execute()
            
            logger.info(f"Updated metadata for video: {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating video metadata: {str(e)}")
            return False
    
    def delete_video(self, video_id: str) -> bool:
        """Delete a video from YouTube"""
        if not self.youtube_service:
            logger.error("YouTube service not initialized")
            return False
        
        try:
            request = self.youtube_service.videos().delete(id=video_id)
            request.execute()
            
            logger.info(f"Deleted video: {video_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting video: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if the service is properly authenticated"""
        return self.youtube_service is not None and self.credentials is not None
    
    def get_upload_quota_usage(self) -> Optional[Dict]:
        """Get current quota usage information"""
        # Note: This is a simplified version. Real quota tracking would require
        # more sophisticated monitoring of API calls
        return {
            'daily_upload_limit': 6,  # YouTube default for new channels
            'estimated_usage': 0,  # Would track actual usage
            'quota_reset_time': '00:00 UTC'
        }

