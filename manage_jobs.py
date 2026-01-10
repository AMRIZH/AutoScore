"""
Script to reset stuck jobs for testing.
Run this to clear the old stuck jobs and test again.
"""

import os
import sys
import shutil

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import Job, JobResult

def reset_stuck_jobs():
    """Reset all stuck jobs (processing status) to failed or delete them."""
    app = create_app()
    
    with app.app_context():
        # Find stuck jobs
        stuck_jobs = Job.query.filter(Job.status == 'processing').all()
        
        if not stuck_jobs:
            print("✓ Tidak ada job yang stuck")
            return
        
        print(f"Ditemukan {len(stuck_jobs)} job stuck:")
        for job in stuck_jobs:
            print(f"  - Job #{job.id}: {job.total_files} files, created {job.created_at}")
            
            # Delete associated job results
            JobResult.query.filter_by(job_id=job.id).delete()
            
            # Delete the job
            db.session.delete(job)
            
            # Clean up upload folder if exists
            job_folder = os.path.join(app.config['UPLOAD_FOLDER'], f"job_{job.id}")
            if os.path.exists(job_folder):
                shutil.rmtree(job_folder)
                print(f"    → Folder dihapus: {job_folder}")
        
        db.session.commit()
        print(f"\n✓ {len(stuck_jobs)} stuck job berhasil dihapus")

def show_job_status():
    """Show current status of all jobs."""
    app = create_app()
    
    with app.app_context():
        jobs = Job.query.order_by(Job.created_at.desc()).limit(10).all()
        
        if not jobs:
            print("Tidak ada job")
            return
        
        print(f"\n{'='*60}")
        print(f"{'Job ID':<8} {'Status':<12} {'Files':<10} {'Message':<30}")
        print(f"{'='*60}")
        
        for job in jobs:
            files_info = f"{job.processed_files or 0}/{job.total_files}"
            message = (job.status_message or '-')[:30]
            print(f"{job.id:<8} {job.status:<12} {files_info:<10} {message:<30}")
        
        print(f"{'='*60}\n")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage AutoScoring jobs')
    parser.add_argument('action', choices=['status', 'reset'], help='Action to perform')
    args = parser.parse_args()
    
    if args.action == 'status':
        show_job_status()
    elif args.action == 'reset':
        show_job_status()
        confirm = input("Reset semua stuck jobs? (y/n): ")
        if confirm.lower() == 'y':
            reset_stuck_jobs()
            show_job_status()
        else:
            print("Dibatalkan")
