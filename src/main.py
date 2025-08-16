import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, current_app
from flask_cors import CORS
from src.models.user import db
from src.models.pipeline import VideoGeneration, ScheduledJob, SystemStatus, ApiUsage
from src.routes.user import user_bp
from src.routes.automation import automation_bp
from src.utils.logger import automation_logger
import logging

# Set up enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')

# Enable CORS for all routes
CORS(app)

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/api')
app.register_blueprint(automation_bp, url_prefix='/api/automation')

# Database configuration
database_url = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(os.path.dirname(__file__), 'database', 'app.db')}")
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database (use single db instance)
db.init_app(app)

with app.app_context():
    db.create_all()
    automation_logger.logger.info("YouTube Automation System started")
    automation_logger.logger.info(f"Database: {database_url}")
    automation_logger.logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")

# Media file serving routes
@app.route('/media/<path:filename>')
def serve_media(filename):
    """Serve media files (videos, images) directly"""
    media_dir = os.path.join(os.path.dirname(__file__), '..', 'media')
    media_path = os.path.abspath(media_dir)
    
    automation_logger.logger.info(f"Media file requested: {filename}")
    automation_logger.logger.debug(f"Media directory: {media_path}")
    
    if not os.path.exists(media_path):
        automation_logger.logger.error(f"Media directory not found: {media_path}")
        return "Media directory not found", 404
    
    file_path = os.path.join(media_path, filename)
    if not os.path.exists(file_path):
        automation_logger.logger.warning(f"Media file not found: {file_path}")
        return "File not found", 404
    
    # Security check - ensure file is within media directory
    if not os.path.abspath(file_path).startswith(media_path):
        automation_logger.logger.error(f"Security violation: attempted access outside media directory: {file_path}")
        return "Access denied", 403
    
    automation_logger.logger.info(f"Serving media file: {filename}")
    return send_from_directory(media_path, filename)

@app.route('/app/media/<path:filename>')
def serve_app_media(filename):
    """Serve media files with /app prefix for compatibility"""
    return serve_media(filename)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    automation_logger.logger.info("Starting Flask development server")
    app.run(host='0.0.0.0', port=5000, debug=False)
