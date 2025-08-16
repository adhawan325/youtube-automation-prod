from src.models.user import db
from datetime import datetime
import json

class VideoGeneration(db.Model):
    """Model for tracking video generation jobs"""
    __tablename__ = 'video_generations'
    
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(50), nullable=False, default='pending')  # pending, processing, completed, failed
    title = db.Column(db.String(200), nullable=True)
    description = db.Column(db.Text, nullable=True)
    script_content = db.Column(db.Text, nullable=True)
    video_file_path = db.Column(db.String(500), nullable=True)
    youtube_video_id = db.Column(db.String(100), nullable=True)
    youtube_url = db.Column(db.String(500), nullable=True)
    
    # Metadata
    duration_seconds = db.Column(db.Float, nullable=True)
    file_size_mb = db.Column(db.Float, nullable=True)
    media_assets_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Error tracking
    error_message = db.Column(db.Text, nullable=True)
    retry_count = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'title': self.title,
            'description': self.description,
            'video_file_path': self.video_file_path,
            'youtube_video_id': self.youtube_video_id,
            'youtube_url': self.youtube_url,
            'duration_seconds': self.duration_seconds,
            'file_size_mb': self.file_size_mb,
            'media_assets_count': self.media_assets_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count
        }

class ScheduledJob(db.Model):
    """Model for tracking scheduled video generation jobs"""
    __tablename__ = 'scheduled_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_type = db.Column(db.String(50), nullable=False, default='video_generation')
    status = db.Column(db.String(50), nullable=False, default='active')  # active, paused, disabled
    
    # Schedule configuration
    interval_hours = db.Column(db.Integer, default=1)  # Generate every X hours
    next_run_at = db.Column(db.DateTime, nullable=False)
    last_run_at = db.Column(db.DateTime, nullable=True)
    
    # Job configuration
    config_json = db.Column(db.Text, nullable=True)  # JSON configuration for the job
    
    # Statistics
    total_runs = db.Column(db.Integer, default=0)
    successful_runs = db.Column(db.Integer, default=0)
    failed_runs = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_type': self.job_type,
            'status': self.status,
            'interval_hours': self.interval_hours,
            'next_run_at': self.next_run_at.isoformat() if self.next_run_at else None,
            'last_run_at': self.last_run_at.isoformat() if self.last_run_at else None,
            'config': json.loads(self.config_json) if self.config_json else {},
            'total_runs': self.total_runs,
            'successful_runs': self.successful_runs,
            'failed_runs': self.failed_runs,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SystemStatus(db.Model):
    """Model for tracking system status and health"""
    __tablename__ = 'system_status'
    
    id = db.Column(db.Integer, primary_key=True)
    component = db.Column(db.String(100), nullable=False)  # news_api, openai, pexels, youtube, etc.
    status = db.Column(db.String(50), nullable=False)  # healthy, warning, error
    last_check_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Status details
    response_time_ms = db.Column(db.Float, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)  # Additional status info
    
    def to_dict(self):
        return {
            'id': self.id,
            'component': self.component,
            'status': self.status,
            'last_check_at': self.last_check_at.isoformat() if self.last_check_at else None,
            'response_time_ms': self.response_time_ms,
            'error_message': self.error_message,
            'metadata': json.loads(self.metadata_json) if self.metadata_json else {}
        }

class ApiUsage(db.Model):
    """Model for tracking API usage and costs"""
    __tablename__ = 'api_usage'
    
    id = db.Column(db.Integer, primary_key=True)
    service = db.Column(db.String(100), nullable=False)  # newsapi, openai, pexels, youtube
    endpoint = db.Column(db.String(200), nullable=True)
    
    # Usage metrics
    requests_count = db.Column(db.Integer, default=1)
    tokens_used = db.Column(db.Integer, nullable=True)  # For OpenAI
    estimated_cost = db.Column(db.Float, nullable=True)
    
    # Timestamps
    date = db.Column(db.Date, default=datetime.utcnow().date())
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'service': self.service,
            'endpoint': self.endpoint,
            'requests_count': self.requests_count,
            'tokens_used': self.tokens_used,
            'estimated_cost': self.estimated_cost,
            'date': self.date.isoformat() if self.date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

