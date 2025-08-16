from datetime import datetime, timedelta
import logging
import threading
import time
import os
import sys
from flask import Blueprint, jsonify, request, send_file, abort, current_app
from werkzeug.utils import secure_filename

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from src.models.pipeline import db, VideoGeneration, ScheduledJob, SystemStatus, ApiUsage
from src.services.pipeline_orchestrator import PipelineOrchestrator
from src.utils.logger import automation_logger

automation_bp = Blueprint('automation', __name__)
logger = logging.getLogger(__name__)

# Global scheduler thread
scheduler_thread = None
scheduler_running = False

@automation_bp.route('/status', methods=['GET'])
def get_system_status():
    """Get overall system status with enhanced logging"""
    try:
        automation_logger.logger.info("System status requested")
        
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
        
        automation_logger.logger.debug(f"System status: total={total_videos}, successful={successful_videos}, failed={failed_videos}")
        
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
        automation_logger.logger.error(f"Error getting system status: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/videos', methods=['GET'])
def get_videos():
    """Get video generation history with enhanced data"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status_filter = request.args.get('status')
        
        automation_logger.logger.debug(f"Videos requested: page={page}, per_page={per_page}, status={status_filter}")
        
        query = VideoGeneration.query
        
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        videos = query.order_by(VideoGeneration.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Enhance video data with file existence check
        enhanced_videos = []
        for video in videos.items:
            video_dict = video.to_dict()
            
            # Check if video file exists and add preview URL
            if video.video_file_path and os.path.exists(video.video_file_path):
                video_dict['has_local_file'] = True
                video_dict['preview_url'] = f'/api/automation/video/{video.id}/preview'
                video_dict['download_url'] = f'/api/automation/video/{video.id}/download'
                
                # Get file size if not stored
                if not video.file_size_mb:
                    try:
                        file_size = os.path.getsize(video.video_file_path)
                        video_dict['file_size_mb'] = file_size / (1024 * 1024)
                    except:
                        pass
            else:
                video_dict['has_local_file'] = False
                video_dict['preview_url'] = None
                video_dict['download_url'] = None
            
            enhanced_videos.append(video_dict)
        
        automation_logger.logger.info(f"Returned {len(enhanced_videos)} videos")
        
        return jsonify({
            'success': True,
            'videos': enhanced_videos,
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
        automation_logger.logger.error(f"Error getting videos: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/video/<int:video_id>/preview', methods=['GET'])
def preview_video(video_id):
    """Serve video file for preview"""
    try:
        automation_logger.logger.info(f"Video preview requested for ID: {video_id}")
        
        video = VideoGeneration.query.get_or_404(video_id)
        
        if not video.video_file_path or not os.path.exists(video.video_file_path):
            automation_logger.logger.warning(f"Video file not found for ID: {video_id}")
            abort(404)
        
        automation_logger.logger.debug(f"Serving video file: {video.video_file_path}")
        
        return send_file(
            video.video_file_path,
            mimetype='video/mp4',
            as_attachment=False,
            download_name=f"video_{video_id}.mp4"
        )
        
    except Exception as e:
        automation_logger.logger.error(f"Error serving video preview {video_id}: {str(e)}")
        abort(500)

@automation_bp.route('/video/<int:video_id>/download', methods=['GET'])
def download_video(video_id):
    """Download video file"""
    try:
        automation_logger.logger.info(f"Video download requested for ID: {video_id}")
        
        video = VideoGeneration.query.get_or_404(video_id)
        
        if not video.video_file_path or not os.path.exists(video.video_file_path):
            automation_logger.logger.warning(f"Video file not found for download ID: {video_id}")
            abort(404)
        
        filename = f"{secure_filename(video.title or f'video_{video_id}')}.mp4"
        automation_logger.logger.debug(f"Downloading video file: {video.video_file_path} as {filename}")
        
        return send_file(
            video.video_file_path,
            mimetype='video/mp4',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        automation_logger.logger.error(f"Error downloading video {video_id}: {str(e)}")
        abort(500)

@automation_bp.route('/generate-video', methods=['POST'])
def generate_video_manual():
    """Manually trigger video generation with enhanced logging"""
    try:
        automation_logger.logger.info("Manual video generation requested")
        
        # Create new video generation record
        video_gen = VideoGeneration(
            status='pending',
            created_at=datetime.utcnow()
        )
        db.session.add(video_gen)
        db.session.commit()
        
        automation_logger.log_pipeline_step(
            step_name="manual_video_generation_initiated",
            status="SUCCESS",
            details={"video_id": video_gen.id}
        )
        
        # Start video generation in background thread
        def generate_video_thread():
            # Create a new app context for this thread
            app = current_app._get_current_object()
            with app.app_context():
                try:
                    automation_logger.logger.info(f"Starting video generation thread for ID: {video_gen.id}")
                    
                    orchestrator = PipelineOrchestrator()
                    result = orchestrator.generate_complete_video()
                    
                    if result and result.get('success'):
                        # Update video record with results
                        video_gen.status = 'completed'
                        video_gen.title = result.get('title')
                        video_gen.description = result.get('description')
                        video_gen.video_file_path = result.get('video_file_path')
                        video_gen.youtube_video_id = result.get('youtube_video_id')
                        video_gen.youtube_url = result.get('youtube_url')
                        video_gen.duration_seconds = result.get('duration_seconds')
                        video_gen.file_size_mb = result.get('file_size_mb')
                        video_gen.completed_at = datetime.utcnow()
                        
                        automation_logger.log_video_generation(
                            video_id=video_gen.id,
                            status="SUCCESS",
                            duration=result.get('duration_seconds'),
                            file_size=result.get('file_size_mb')
                        )
                        
                        automation_logger.logger.info(f"Video generation completed successfully for ID: {video_gen.id}")
                    else:
                        video_gen.status = 'failed'
                        video_gen.error_message = result.get('error', 'Unknown error') if result else 'Pipeline returned no result'
                        video_gen.completed_at = datetime.utcnow()
                        
                        automation_logger.log_video_generation(
                            video_id=video_gen.id,
                            status="FAILED",
                            error=video_gen.error_message
                        )
                        
                        automation_logger.logger.error(f"Video generation failed for ID: {video_gen.id}, error: {video_gen.error_message}")
                    
                    db.session.commit()
                    
                except Exception as e:
                    automation_logger.logger.error(f"Error in video generation thread: {str(e)}")
                    video_gen.status = 'failed'
                    video_gen.error_message = str(e)
                    video_gen.completed_at = datetime.utcnow()
                    db.session.commit()
                    
                    automation_logger.log_video_generation(
                        video_id=video_gen.id,
                        status="FAILED",
                        error=str(e)
                    )
        
        # Start the thread
        thread = threading.Thread(target=generate_video_thread)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Video generation started',
            'video_id': video_gen.id
        })
        
    except Exception as e:
        automation_logger.logger.error(f"Error starting manual video generation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/scheduler/start', methods=['POST'])
def start_scheduler():
    """Start the video generation scheduler with enhanced logging"""
    global scheduler_thread, scheduler_running
    
    try:
        automation_logger.logger.info("Scheduler start requested")
        
        if scheduler_running:
            automation_logger.logger.warning("Scheduler already running")
            return jsonify({'success': False, 'error': 'Scheduler already running'})
        
        def scheduler_loop():
            global scheduler_running
            scheduler_running = True
            
            # Get the app instance for this thread
            app = current_app._get_current_object()
            
            automation_logger.logger.info("Scheduler loop started")
            
            while scheduler_running:
                try:
                    with app.app_context():
                        automation_logger.logger.debug("Scheduler tick - checking for scheduled jobs")
                        
                        # Check for scheduled jobs
                        now = datetime.utcnow()
                        due_jobs = ScheduledJob.query.filter(
                            ScheduledJob.status == 'active',
                            ScheduledJob.next_run_at <= now
                        ).all()
                        
                        automation_logger.logger.info(f"Found {len(due_jobs)} due jobs")
                        
                        for job in due_jobs:
                            automation_logger.logger.info(f"Executing scheduled job: {job.id}")
                            
                            # Generate video
                            video_gen = VideoGeneration(
                                status='pending',
                                created_at=datetime.utcnow()
                            )
                            db.session.add(video_gen)
                            db.session.commit()
                            
                            try:
                                orchestrator = PipelineOrchestrator()
                                result = orchestrator.generate_complete_video()
                                
                                if result and result.get('success'):
                                    video_gen.status = 'completed'
                                    video_gen.title = result.get('title')
                                    video_gen.description = result.get('description')
                                    video_gen.video_file_path = result.get('video_file_path')
                                    video_gen.youtube_video_id = result.get('youtube_video_id')
                                    video_gen.youtube_url = result.get('youtube_url')
                                    video_gen.duration_seconds = result.get('duration_seconds')
                                    video_gen.file_size_mb = result.get('file_size_mb')
                                    video_gen.completed_at = datetime.utcnow()
                                    
                                    job.successful_runs += 1
                                    automation_logger.logger.info(f"Scheduled job {job.id} completed successfully")
                                else:
                                    video_gen.status = 'failed'
                                    video_gen.error_message = result.get('error', 'Unknown error') if result else 'Pipeline returned no result'
                                    video_gen.completed_at = datetime.utcnow()
                                    
                                    job.failed_runs += 1
                                    automation_logger.logger.error(f"Scheduled job {job.id} failed: {video_gen.error_message}")
                                
                            except Exception as e:
                                video_gen.status = 'failed'
                                video_gen.error_message = str(e)
                                video_gen.completed_at = datetime.utcnow()
                                job.failed_runs += 1
                                automation_logger.logger.error(f"Error in scheduled job {job.id}: {str(e)}")
                            
                            # Update job schedule
                            job.last_run_at = now
                            job.next_run_at = now + timedelta(hours=job.interval_hours)
                            job.total_runs += 1
                            
                            db.session.commit()
                        
                        # Sleep for 60 seconds before next check
                        time.sleep(60)
                        
                except Exception as e:
                    automation_logger.logger.error(f"Error in scheduler loop: {str(e)}")
                    time.sleep(60)  # Continue after error
            
            automation_logger.logger.info("Scheduler loop stopped")
        
        scheduler_thread = threading.Thread(target=scheduler_loop)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # Create or update scheduled job record
        job = ScheduledJob.query.filter_by(job_type='video_generation').first()
        if not job:
            job = ScheduledJob(
                job_type='video_generation',
                status='active',
                interval_hours=1,
                next_run_at=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(job)
        else:
            job.status = 'active'
            job.next_run_at = datetime.utcnow() + timedelta(hours=job.interval_hours)
        
        db.session.commit()
        
        automation_logger.log_pipeline_step(
            step_name="scheduler_started",
            status="SUCCESS",
            details={"interval_hours": job.interval_hours}
        )
        
        return jsonify({'success': True, 'message': 'Scheduler started'})
        
    except Exception as e:
        automation_logger.logger.error(f"Error starting scheduler: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """Stop the video generation scheduler with enhanced logging"""
    global scheduler_running
    
    try:
        automation_logger.logger.info("Scheduler stop requested")
        
        if not scheduler_running:
            automation_logger.logger.warning("Scheduler not running")
            return jsonify({'success': False, 'error': 'Scheduler not running'})
        
        scheduler_running = False
        
        # Update scheduled job status
        job = ScheduledJob.query.filter_by(job_type='video_generation').first()
        if job:
            job.status = 'paused'
            db.session.commit()
        
        automation_logger.log_pipeline_step(
            step_name="scheduler_stopped",
            status="SUCCESS",
            details={}
        )
        
        return jsonify({'success': True, 'message': 'Scheduler stopped'})
        
    except Exception as e:
        automation_logger.logger.error(f"Error stopping scheduler: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@automation_bp.route('/logs', methods=['GET'])
def get_logs():
    """Get recent log entries"""
    try:
        log_type = request.args.get('type', 'all')  # all, api, errors
        limit = request.args.get('limit', 100, type=int)
        
        automation_logger.logger.debug(f"Logs requested: type={log_type}, limit={limit}")
        
        logs = []
        
        # Read from log files
        log_files = {
            'all': 'logs/youtube_automation.log',
            'api': 'logs/api_calls.log',
            'errors': 'logs/errors.log'
        }
        
        log_file = log_files.get(log_type, log_files['all'])
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Get last N lines
                recent_lines = lines[-limit:] if len(lines) > limit else lines
                logs = [line.strip() for line in recent_lines if line.strip()]
        
        return jsonify({
            'success': True,
            'logs': logs,
            'log_type': log_type,
            'count': len(logs)
        })
        
    except Exception as e:
        automation_logger.logger.error(f"Error getting logs: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

