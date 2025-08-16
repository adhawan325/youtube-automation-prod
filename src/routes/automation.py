from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import logging
import threading
import time
import os
import sys

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.models.pipeline import db, VideoGeneration, ScheduledJob, SystemStatus, ApiUsage
from src.services.pipeline_orchestrator import PipelineOrchestrator

automation_bp = Blueprint('automation', __name__)
logger = logging.getLogger(__name__)

# Global scheduler thread
scheduler_thread = None
scheduler_running = False

@automation_bp.route('/status', methods=['GET'])
def get_system_status():
    """Get overall system status"""
    try:
        # Get recent video generations
        recent_videos = VideoGeneration.query.order_by(VideoGeneration.created_at.desc()).limit(10).all()
        
        # Get scheduled jobs
        scheduled_jobs = ScheduledJob.query.all()
        
        # Get system component status
        system_components = SystemStatus.query.all()
        
        # Calculate statistics
        total_videos = VideoGeneration.query.count()
        successful_videos = VideoGeneration.query.filter_by(status='completed').count()
        failed_videos = VideoGeneration.query.filter_by(status='failed').count()
        
        # Get today's API usage
        today = datetime.utcnow().date()
        api_usage_today = ApiUsage.query.filter_by(date=today).all()
        
        return jsonify({
            'success': True,
            'system_status': {
                'scheduler_running': scheduler_running,
                'total_videos': total_videos,
                'successful_videos': successful_videos,
                'failed_videos': failed_videos,
                'success_rate': (successful_videos / total_videos * 100) if total_videos > 0 else 0
            },
            'recent_videos': [video.to_dict() for video in recent_videos],
            'scheduled_jobs': [job.to_dict() for job in scheduled_jobs],
            'system_components': [comp.to_dict() for comp in system_components],
            'api_usage_today': [usage.to_dict() for usage in api_usage_today]
        })
        
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/videos', methods=['GET'])
def get_videos():
    """Get video generation history"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')
        
        query = VideoGeneration.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        videos = query.order_by(VideoGeneration.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'success': True,
            'videos': [video.to_dict() for video in videos.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': videos.total,
                'pages': videos.pages,
                'has_next': videos.has_next,
                'has_prev': videos.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting videos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/generate-video', methods=['POST'])
def generate_video_manual():
    """Manually trigger video generation"""
    try:
        # Create new video generation record
        video_gen = VideoGeneration(
            status='pending',
            created_at=datetime.utcnow()
        )
        db.session.add(video_gen)
        db.session.commit()
        
        # Start video generation in background thread
        thread = threading.Thread(
            target=run_video_generation,
            args=(video_gen.id,)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Video generation started',
            'video_id': video_gen.id
        })
        
    except Exception as e:
        logger.error(f"Error starting manual video generation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/scheduler/start', methods=['POST'])
def start_scheduler():
    """Start the automated scheduler"""
    global scheduler_thread, scheduler_running
    
    try:
        if scheduler_running:
            return jsonify({
                'success': False,
                'message': 'Scheduler is already running'
            })
        
        # Create or update scheduled job
        job = ScheduledJob.query.filter_by(job_type='video_generation').first()
        if not job:
            job = ScheduledJob(
                job_type='video_generation',
                status='active',
                interval_hours=1,
                next_run_at=datetime.utcnow() + timedelta(minutes=1)  # Start in 1 minute
            )
            db.session.add(job)
        else:
            job.status = 'active'
            job.next_run_at = datetime.utcnow() + timedelta(minutes=1)
        
        db.session.commit()
        
        # Start scheduler thread
        scheduler_running = True
        scheduler_thread = threading.Thread(target=scheduler_loop)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Scheduler started successfully'
        })
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Stop the automated scheduler"""
    global scheduler_running
    
    try:
        scheduler_running = False
        
        # Update scheduled job status
        job = ScheduledJob.query.filter_by(job_type='video_generation').first()
        if job:
            job.status = 'paused'
            db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Scheduler stopped successfully'
        })
        
    except Exception as e:
        logger.error(f"Error stopping scheduler: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/scheduler/config', methods=['POST'])
def update_scheduler_config():
    """Update scheduler configuration"""
    try:
        data = request.get_json()
        interval_hours = data.get('interval_hours', 1)
        
        job = ScheduledJob.query.filter_by(job_type='video_generation').first()
        if not job:
            job = ScheduledJob(
                job_type='video_generation',
                status='active',
                interval_hours=interval_hours,
                next_run_at=datetime.utcnow() + timedelta(hours=interval_hours)
            )
            db.session.add(job)
        else:
            job.interval_hours = interval_hours
            # Update next run time based on new interval
            if job.last_run_at:
                job.next_run_at = job.last_run_at + timedelta(hours=interval_hours)
            else:
                job.next_run_at = datetime.utcnow() + timedelta(hours=interval_hours)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Scheduler configuration updated',
            'config': job.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating scheduler config: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

def scheduler_loop():
    """Main scheduler loop that runs in background"""
    global scheduler_running
    
    logger.info("Scheduler loop started")
    
    while scheduler_running:
        try:
            # Check for jobs that need to run
            now = datetime.utcnow()
            jobs_to_run = ScheduledJob.query.filter(
                ScheduledJob.status == 'active',
                ScheduledJob.next_run_at <= now
            ).all()
            
            for job in jobs_to_run:
                logger.info(f"Running scheduled job: {job.job_type}")
                
                # Create video generation record
                video_gen = VideoGeneration(
                    status='pending',
                    created_at=datetime.utcnow()
                )
                db.session.add(video_gen)
                db.session.commit()
                
                # Run video generation in separate thread
                thread = threading.Thread(
                    target=run_video_generation,
                    args=(video_gen.id,)
                )
                thread.daemon = True
                thread.start()
                
                # Update job schedule
                job.last_run_at = now
                job.next_run_at = now + timedelta(hours=job.interval_hours)
                job.total_runs += 1
                db.session.commit()
            
            # Sleep for 30 seconds before checking again
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"Error in scheduler loop: {str(e)}")
            time.sleep(60)  # Wait longer on error
    
    logger.info("Scheduler loop stopped")

def run_video_generation(video_id):
    """Run video generation for a specific video ID"""
    from src.main import app
    
    with app.app_context():
        try:
            # Get video generation record
            video_gen = VideoGeneration.query.get(video_id)
            if not video_gen:
                logger.error(f"Video generation record not found: {video_id}")
                return
            
            # Update status
            video_gen.status = 'processing'
            video_gen.started_at = datetime.utcnow()
            db.session.commit()
            
            # Initialize pipeline orchestrator
            orchestrator = PipelineOrchestrator()
            
            # Run complete pipeline
            result = orchestrator.run_complete_pipeline()
            
            if result and result.get('success'):
                # Update video record with results
                video_gen.status = 'completed'
                video_gen.completed_at = datetime.utcnow()
                video_gen.title = result.get('title', '')
                video_gen.description = result.get('description', '')
                video_gen.script_content = result.get('script', '')
                video_gen.video_file_path = result.get('video_path', '')
                video_gen.youtube_video_id = result.get('youtube_video_id', '')
                video_gen.youtube_url = result.get('youtube_url', '')
                video_gen.duration_seconds = result.get('duration', 0)
                video_gen.file_size_mb = result.get('file_size_mb', 0)
                video_gen.media_assets_count = result.get('media_count', 0)
                
                # Update job success count
                job = ScheduledJob.query.filter_by(job_type='video_generation').first()
                if job:
                    job.successful_runs += 1
                
            else:
                # Handle failure
                video_gen.status = 'failed'
                video_gen.completed_at = datetime.utcnow()
                video_gen.error_message = result.get('error', 'Unknown error') if result else 'Pipeline failed'
                
                # Update job failure count
                job = ScheduledJob.query.filter_by(job_type='video_generation').first()
                if job:
                    job.failed_runs += 1
            
            db.session.commit()
            logger.info(f"Video generation completed: {video_id} - Status: {video_gen.status}")
            
        except Exception as e:
            logger.error(f"Error in video generation {video_id}: {str(e)}")
            
            # Update video record with error
            try:
                video_gen = VideoGeneration.query.get(video_id)
                if video_gen:
                    video_gen.status = 'failed'
                    video_gen.completed_at = datetime.utcnow()
                    video_gen.error_message = str(e)
                    video_gen.retry_count += 1
                    db.session.commit()
            except Exception as db_error:
                logger.error(f"Failed to update video record: {str(db_error)}")

