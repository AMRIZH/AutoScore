"""
Cleanup service for AutoScoring application.
Handles temporary file cleanup on startup and scheduled intervals.
"""

import os
import shutil
import logging
from datetime import datetime

from app.models import Job, SystemLog

logger = logging.getLogger(__name__)


def cleanup_temp_files(app):
    """
    Clean up temporary upload files.
    Called on application startup and by scheduled task.
    
    Args:
        app: Flask application instance
    """
    from app.extensions import db
    
    upload_folder = app.config.get('UPLOAD_FOLDER')
    
    if not upload_folder or not os.path.exists(upload_folder):
        logger.info("Folder upload tidak ditemukan, tidak ada yang perlu dibersihkan")
        return
    
    logger.info(f"Memulai pembersihan folder: {upload_folder}")
    
    # Get list of active job IDs (processing status)
    active_job_ids = set()
    with app.app_context():
        active_jobs = Job.query.filter_by(status='processing').all()
        # Note: Job folders are named with UUID, not job ID
        # We need to preserve folders for processing jobs
        # Since we can't easily map job_id to folder, we'll skip cleanup
        # if there are any active jobs
        if active_jobs:
            logger.warning(f"Ada {len(active_jobs)} job yang sedang diproses, melewatkan pembersihan")
            return
    
    # Count files before cleanup
    files_deleted = 0
    folders_deleted = 0
    
    try:
        for item in os.listdir(upload_folder):
            item_path = os.path.join(upload_folder, item)
            
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    files_deleted += 1
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                    folders_deleted += 1
            except Exception as e:
                logger.error(f"Gagal menghapus {item_path}: {e}")
        
        logger.info(f"Pembersihan selesai: {folders_deleted} folder, {files_deleted} file dihapus")
        
        # Log to database
        with app.app_context():
            SystemLog.log(
                'INFO', 'cleanup',
                f'Pembersihan file: {folders_deleted} folder, {files_deleted} file dihapus',
                details=f'{{"folders": {folders_deleted}, "files": {files_deleted}}}'
            )
            
    except Exception as e:
        logger.error(f"Error saat pembersihan: {e}")
        with app.app_context():
            SystemLog.log('ERROR', 'cleanup', f'Error pembersihan: {e}')


def scheduled_cleanup(app):
    """
    Scheduled cleanup task - runs at 02:00 WIB daily.
    
    Args:
        app: Flask application instance
    """
    logger.info(f"Menjalankan pembersihan terjadwal: {datetime.now()}")
    cleanup_temp_files(app)


def cleanup_old_results(app, days_old: int = 30):
    """
    Clean up old result CSV files.
    
    Args:
        app: Flask application instance
        days_old: Delete files older than this many days
    """
    from datetime import timedelta
    
    results_folder = app.config.get('RESULTS_FOLDER')
    
    if not results_folder or not os.path.exists(results_folder):
        return
    
    cutoff_time = datetime.now() - timedelta(days=days_old)
    files_deleted = 0
    
    for filename in os.listdir(results_folder):
        filepath = os.path.join(results_folder, filename)
        
        if os.path.isfile(filepath):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            if file_mtime < cutoff_time:
                try:
                    os.remove(filepath)
                    files_deleted += 1
                except Exception as e:
                    logger.error(f"Gagal menghapus file hasil lama {filepath}: {e}")
    
    if files_deleted > 0:
        logger.info(f"Menghapus {files_deleted} file hasil yang lebih dari {days_old} hari")
