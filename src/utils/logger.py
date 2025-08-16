"""
Enhanced logging configuration for YouTube automation system
"""
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
import json

class YouTubeAutomationLogger:
    """Custom logger for YouTube automation with structured logging"""
    
    def __init__(self, name="youtube_automation"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
            
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # Console handler with color coding
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler for all logs
        file_handler = RotatingFileHandler(
            'logs/youtube_automation.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        # Error handler for critical issues
        error_handler = RotatingFileHandler(
            'logs/errors.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        
        # API handler for API-specific logs
        api_handler = RotatingFileHandler(
            'logs/api_calls.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        api_handler.setLevel(logging.DEBUG)
        api_formatter = logging.Formatter(
            '%(asctime)s - API - %(levelname)s - %(message)s'
        )
        api_handler.setFormatter(api_formatter)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        
        # Create API logger
        self.api_logger = logging.getLogger(f"{name}.api")
        self.api_logger.setLevel(logging.DEBUG)
        self.api_logger.addHandler(api_handler)
        self.api_logger.addHandler(console_handler)
    
    def log_api_call(self, service, endpoint, method="GET", params=None, response_status=None, response_data=None, error=None):
        """Log API calls with structured data"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "service": service,
            "endpoint": endpoint,
            "method": method,
            "params": params,
            "response_status": response_status,
            "error": str(error) if error else None
        }
        
        if error:
            self.api_logger.error(f"API_CALL_FAILED: {json.dumps(log_data, indent=2)}")
        else:
            self.api_logger.info(f"API_CALL_SUCCESS: {json.dumps(log_data, indent=2)}")
    
    def log_pipeline_step(self, step_name, status, details=None, duration=None):
        """Log pipeline steps with timing"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "step": step_name,
            "status": status,
            "details": details,
            "duration_seconds": duration
        }
        
        if status == "FAILED":
            self.logger.error(f"PIPELINE_STEP_FAILED: {json.dumps(log_data, indent=2)}")
        elif status == "SUCCESS":
            self.logger.info(f"PIPELINE_STEP_SUCCESS: {json.dumps(log_data, indent=2)}")
        else:
            self.logger.info(f"PIPELINE_STEP: {json.dumps(log_data, indent=2)}")
    
    def log_media_discovery(self, query, found_count, service, details=None):
        """Log media discovery results"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "found_count": found_count,
            "service": service,
            "details": details
        }
        
        if found_count == 0:
            self.logger.warning(f"NO_MEDIA_FOUND: {json.dumps(log_data, indent=2)}")
        else:
            self.logger.info(f"MEDIA_DISCOVERED: {json.dumps(log_data, indent=2)}")
    
    def log_video_generation(self, video_id, status, duration=None, file_size=None, error=None):
        """Log video generation results"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "video_id": video_id,
            "status": status,
            "duration_seconds": duration,
            "file_size_mb": file_size,
            "error": str(error) if error else None
        }
        
        if status == "FAILED":
            self.logger.error(f"VIDEO_GENERATION_FAILED: {json.dumps(log_data, indent=2)}")
        else:
            self.logger.info(f"VIDEO_GENERATION: {json.dumps(log_data, indent=2)}")
    
    def log_youtube_upload(self, video_id, youtube_id=None, status="PENDING", error=None):
        """Log YouTube upload attempts"""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "local_video_id": video_id,
            "youtube_video_id": youtube_id,
            "status": status,
            "error": str(error) if error else None
        }
        
        if status == "FAILED":
            self.logger.error(f"YOUTUBE_UPLOAD_FAILED: {json.dumps(log_data, indent=2)}")
        elif status == "SUCCESS":
            self.logger.info(f"YOUTUBE_UPLOAD_SUCCESS: {json.dumps(log_data, indent=2)}")
        else:
            self.logger.info(f"YOUTUBE_UPLOAD: {json.dumps(log_data, indent=2)}")

# Global logger instance
automation_logger = YouTubeAutomationLogger()

