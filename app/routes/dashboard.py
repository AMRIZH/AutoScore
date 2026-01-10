"""
Dashboard routes for AutoScoring application.
"""

import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, Response, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Job, JobResult, SystemLog
from app.services.scoring_service import ScoringService

dashboard_bp = Blueprint('dashboard', __name__)

# Store for job progress (in-memory, could use Redis in production)
job_progress = {}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def validate_pdf(file):
    """Validate PDF file thoroughly."""
    errors = []
    
    # Check filename extension
    if not file.filename:
        errors.append('Nama file tidak valid.')
        return errors
    
    if not allowed_file(file.filename):
        errors.append(f'File {file.filename} bukan format PDF.')
        return errors
    
    # Check MIME type
    if file.content_type not in ['application/pdf', 'application/x-pdf']:
        errors.append(f'File {file.filename} memiliki tipe MIME tidak valid: {file.content_type}')
    
    # Check PDF magic bytes (header)
    file.seek(0)
    header = file.read(5)
    file.seek(0)  # Reset file pointer
    
    if header != b'%PDF-':
        errors.append(f'File {file.filename} bukan file PDF yang valid (header tidak sesuai).')
    
    return errors


@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Main dashboard page."""
    # Get user's recent jobs
    recent_jobs = Job.query.filter_by(user_id=current_user.id)\
        .order_by(Job.created_at.desc())\
        .limit(10).all()
    
    return render_template('dashboard.html', 
                          recent_jobs=recent_jobs,
                          max_pdf_count=current_app.config['MAX_PDF_COUNT'],
                          default_score_min=current_app.config['DEFAULT_SCORE_MIN'],
                          default_score_max=current_app.config['DEFAULT_SCORE_MAX'])


@dashboard_bp.route('/api/upload', methods=['POST'])
@login_required
def upload_files():
    """Handle file upload and create scoring job."""
    try:
        # Get form data
        score_min = int(request.form.get('score_min', current_app.config['DEFAULT_SCORE_MIN']))
        score_max = int(request.form.get('score_max', current_app.config['DEFAULT_SCORE_MAX']))
        enable_evaluation = request.form.get('enable_evaluation', 'true').lower() == 'true'
        
        # Validate score range
        if score_min >= score_max:
            return jsonify({'success': False, 'error': 'Nilai minimum harus lebih kecil dari nilai maksimum.'}), 400
        
        if score_min < 0 or score_max > 100:
            return jsonify({'success': False, 'error': 'Rentang nilai harus antara 0 dan 100.'}), 400
        
        # Get student files
        student_files = request.files.getlist('student_files')
        
        if not student_files or len(student_files) == 0:
            return jsonify({'success': False, 'error': 'Tidak ada file mahasiswa yang diunggah.'}), 400
        
        # Check file count limit
        max_count = current_app.config['MAX_PDF_COUNT']
        if len(student_files) > max_count:
            return jsonify({'success': False, 'error': f'Jumlah file melebihi batas maksimum ({max_count} file).'}), 400
        
        # Validate all PDF files
        all_errors = []
        valid_files = []
        
        for file in student_files:
            if file.filename:
                errors = validate_pdf(file)
                if errors:
                    all_errors.extend(errors)
                else:
                    valid_files.append(file)
        
        if all_errors:
            return jsonify({'success': False, 'error': ' '.join(all_errors)}), 400
        
        if not valid_files:
            return jsonify({'success': False, 'error': 'Tidak ada file PDF yang valid.'}), 400
        
        # Create job folder
        job_id = str(uuid.uuid4())
        job_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], job_id)
        os.makedirs(job_folder, exist_ok=True)
        
        # Save student files
        student_folder = os.path.join(job_folder, 'students')
        os.makedirs(student_folder, exist_ok=True)
        
        saved_files = []
        for file in valid_files:
            filename = secure_filename(file.filename)
            # Add UUID prefix to avoid duplicates
            unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
            filepath = os.path.join(student_folder, unique_filename)
            file.save(filepath)
            saved_files.append({
                'original_name': file.filename,
                'saved_name': unique_filename,
                'path': filepath
            })
        
        # Handle answer key (optional)
        answer_key_path = None
        answer_key_file = request.files.get('answer_key')
        if answer_key_file and answer_key_file.filename:
            ak_errors = validate_pdf(answer_key_file)
            if ak_errors:
                return jsonify({'success': False, 'error': f'Kunci jawaban tidak valid: {" ".join(ak_errors)}'}), 400
            
            ak_filename = secure_filename(answer_key_file.filename)
            answer_key_path = os.path.join(job_folder, f"answer_key_{ak_filename}")
            answer_key_file.save(answer_key_path)
        
        # Create job in database
        job = Job(
            user_id=current_user.id,
            score_min=score_min,
            score_max=score_max,
            enable_evaluation=enable_evaluation,
            answer_key_path=answer_key_path,
            total_files=len(saved_files),
            status='pending'
        )
        db.session.add(job)
        db.session.commit()
        
        # Create job results for each file
        for file_info in saved_files:
            result = JobResult(
                job_id=job.id,
                filename=file_info['original_name'],
                status='pending'
            )
            db.session.add(result)
        db.session.commit()
        
        # Log upload
        current_app.logger.info(f'Upload: {len(saved_files)} file oleh {current_user.username}')
        SystemLog.log('INFO', 'upload', 
                     f'Upload {len(saved_files)} file mahasiswa', 
                     user_id=current_user.id,
                     details=json.dumps({'job_id': job.id, 'file_count': len(saved_files)}))
        
        # Initialize progress tracking
        job_progress[job.id] = {
            'status': 'pending',
            'message': 'Menunggu proses...',
            'progress': 0,
            'total': len(saved_files),
            'current': 0
        }
        
        # Start scoring process in background
        scoring_service = ScoringService(current_app._get_current_object())
        scoring_service.start_scoring(job.id, job_folder, saved_files, job_progress)
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'message': f'Berhasil mengunggah {len(saved_files)} file. Proses penilaian dimulai.'
        })
        
    except Exception as e:
        current_app.logger.error(f'Error upload: {str(e)}')
        SystemLog.log('ERROR', 'upload', f'Error upload: {str(e)}', user_id=current_user.id)
        return jsonify({'success': False, 'error': f'Terjadi kesalahan: {str(e)}'}), 500


@dashboard_bp.route('/api/progress/<int:job_id>')
@login_required
def get_progress(job_id):
    """Get job progress via Server-Sent Events (SSE)."""
    def generate():
        """Generate SSE events."""
        import time
        
        while True:
            # Get progress from memory or database
            if job_id in job_progress:
                progress = job_progress[job_id]
            else:
                # Fallback to database
                job = Job.query.get(job_id)
                if job:
                    progress = {
                        'status': job.status,
                        'message': job.status_message or 'Memproses...',
                        'progress': (job.processed_files / job.total_files * 100) if job.total_files > 0 else 0,
                        'total': job.total_files,
                        'current': job.processed_files
                    }
                else:
                    progress = {'status': 'error', 'message': 'Job tidak ditemukan'}
            
            # Send event
            data = json.dumps(progress)
            yield f"data: {data}\n\n"
            
            # Check if completed or failed
            if progress.get('status') in ['completed', 'failed', 'error']:
                break
            
            time.sleep(1)  # Poll every second
    
    return Response(generate(), mimetype='text/event-stream')


@dashboard_bp.route('/api/job/<int:job_id>')
@login_required
def get_job_status(job_id):
    """Get job status as JSON."""
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    
    if not job:
        return jsonify({'success': False, 'error': 'Job tidak ditemukan.'}), 404
    
    # Get results
    results = []
    for result in job.results.all():
        results.append({
            'filename': result.filename,
            'nim': result.nim,
            'student_name': result.student_name,
            'score': result.score,
            'evaluation': result.evaluation,
            'status': result.status,
            'error_message': result.error_message
        })
    
    return jsonify({
        'success': True,
        'job': {
            'id': job.id,
            'status': job.status,
            'status_message': job.status_message,
            'total_files': job.total_files,
            'processed_files': job.processed_files,
            'result_csv_path': job.result_csv_path,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        },
        'results': results
    })


@dashboard_bp.route('/api/download/<int:job_id>')
@login_required
def download_result(job_id):
    """Download result CSV file."""
    job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    
    if not job:
        return jsonify({'success': False, 'error': 'Job tidak ditemukan.'}), 404
    
    if job.status != 'completed':
        return jsonify({'success': False, 'error': 'Job belum selesai.'}), 400
    
    if not job.result_csv_path or not os.path.exists(job.result_csv_path):
        return jsonify({'success': False, 'error': 'File hasil tidak ditemukan.'}), 404
    
    # Generate download filename
    timestamp = job.completed_at.strftime('%Y%m%d_%H%M%S') if job.completed_at else datetime.now().strftime('%Y%m%d_%H%M%S')
    download_name = f"{current_user.username}_{timestamp}.csv"
    
    return send_file(
        job.result_csv_path,
        mimetype='text/csv',
        as_attachment=True,
        download_name=download_name
    )


@dashboard_bp.route('/api/jobs')
@login_required
def list_jobs():
    """List user's jobs."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    jobs = Job.query.filter_by(user_id=current_user.id)\
        .order_by(Job.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'success': True,
        'jobs': [{
            'id': job.id,
            'status': job.status,
            'total_files': job.total_files,
            'processed_files': job.processed_files,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None
        } for job in jobs.items],
        'total': jobs.total,
        'pages': jobs.pages,
        'current_page': jobs.page
    })
