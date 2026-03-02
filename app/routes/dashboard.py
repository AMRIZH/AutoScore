"""
Dashboard routes for AutoScoring application.
"""

import os
import json
import uuid
import zipfile
import io
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app, Response, send_file, stream_with_context
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

from app.extensions import db
from app.models import Job, JobResult, SystemLog
from app.services.scoring_service import ScoringService
from app.services.llm_service import LLMService, PROVIDER_KEY_FIELDS

dashboard_bp = Blueprint('dashboard', __name__)

# Store for job progress (in-memory, could use Redis in production)
job_progress = {}


def _file_size_bytes(file_storage) -> int:
    """Return file size in bytes without consuming the stream."""
    try:
        stream = file_storage.stream
        current_pos = stream.tell()
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(current_pos)
        return size
    except Exception:
        fallback_stream = getattr(file_storage, 'stream', file_storage)
        current_pos = fallback_stream.tell()
        fallback_stream.seek(0, os.SEEK_END)
        size = fallback_stream.tell()
        fallback_stream.seek(current_pos)
        return size


def _validate_file_size(file_storage, max_file_size_bytes: int, label: str) -> str | None:
    """Return localized error message when uploaded file exceeds configured size limit."""
    size_bytes = _file_size_bytes(file_storage)
    if size_bytes > max_file_size_bytes:
        size_mb = size_bytes / (1024 * 1024)
        max_mb = max_file_size_bytes / (1024 * 1024)
        return (
            f'{label} {file_storage.filename} melebihi batas ukuran '
            f'({size_mb:.2f} MB > {max_mb:.0f} MB).'
        )
    return None


def _validate_llm_provider_ready() -> tuple[bool, str]:
    """Ensure the active provider has the required API key before starting jobs."""
    llm_service = LLMService(current_app.config)
    cfg = llm_service._get_active_config()
    provider = cfg.get('provider', 'gemini')

    if provider == 'gemini':
        gemini_keys = [k.strip() for k in (cfg.get('gemini_keys') or []) if k and k.strip()]
        if not gemini_keys:
            return False, (
                'Provider LLM aktif (GEMINI) belum memiliki API key. '
                'Silakan isi minimal satu API key di Admin Panel > Pengaturan LLM sebelum memulai penilaian.'
            )
        return True, ''

    key_field = PROVIDER_KEY_FIELDS.get(provider)
    if not key_field:
        return False, f'Provider LLM tidak dikenal: {provider}'

    key_value = (cfg.get(key_field, '') or '').strip()
    if not key_value:
        return False, (
            f'Provider LLM aktif ({provider.upper()}) belum memiliki API key. '
            'Silakan isi API key di Admin Panel > Pengaturan LLM sebelum memulai penilaian.'
        )

    return True, ''


@dashboard_bp.route('/api/llm-readiness', methods=['GET'])
@login_required
def llm_readiness():
    """Return whether the active LLM provider is ready for scoring jobs."""
    ready, message = _validate_llm_provider_ready()
    llm_service = LLMService(current_app.config)
    cfg = llm_service._get_active_config()
    return jsonify({
        'success': True,
        'ready': ready,
        'provider': cfg.get('provider', 'gemini'),
        'message': message,
    })


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


# Allowed extensions for question documents (PDF, DOCX, plain text, images)
# NOTE: SVG removed due to XSS risk (requires server-side sanitization if needed)
# NOTE: RAW camera formats (cr2, nef, arw) removed - not commonly used for exam docs
QUESTION_DOC_EXTENSIONS = {
    'pdf', 'doc', 'docx',
    # Plain text formats
    'txt', 'md', 'markdown',
    # Images (common raster formats only)
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'heic', 'heif', 
    'tiff', 'tif'
}

# MIME types for question documents validation
QUESTION_DOC_MIME_TYPES = {
    # Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    # Plain text
    'text/plain', 'text/markdown', 'text/x-markdown',
    # Images
    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
    'image/heic', 'image/heif', 'image/tiff',
}

# Magic bytes signatures for file validation
FILE_SIGNATURES = {
    'pdf': b'%PDF-',
    'jpg': b'\xff\xd8\xff',
    'png': b'\x89PNG\r\n\x1a\n',
    'gif': (b'GIF87a', b'GIF89a'),
    'bmp': b'BM',
    'tiff': (b'II\x2a\x00', b'MM\x00\x2a'),
    'webp': b'RIFF',  # followed by size and WEBP
    'zip': b'PK\x03\x04',  # Generic ZIP signature
    'doc': b'\xd0\xcf\x11\xe0',  # OLE2 format
}

# HEIC/HEIF brand codes (ISO Base Media File Format)
# These distinguish HEIC from MP4, MOV, M4A etc.
HEIC_HEIF_BRANDS = {
    b'heic', b'heix', b'hevc', b'hevx',  # HEIC brands
    b'heif', b'heim', b'heis', b'hevs',  # HEIF brands  
    b'mif1', b'msf1',  # MIAF brands
}


def is_valid_docx(file_content: bytes) -> bool:
    """
    Validate DOCX by checking internal ZIP structure for Office Open XML markers.
    Returns True only if it's a genuine Word document, not just any ZIP file.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zf:
            namelist = zf.namelist()
            # DOCX must have [Content_Types].xml at root
            if '[Content_Types].xml' not in namelist:
                return False
            # DOCX must have word/ directory with document.xml
            if 'word/document.xml' not in namelist:
                return False
            # Verify Content_Types contains Word-specific content type
            try:
                content_types = zf.read('[Content_Types].xml').decode('utf-8', errors='ignore')
                if 'application/vnd.openxmlformats-officedocument.wordprocessingml' not in content_types:
                    return False
            except:
                return False
            return True
    except (zipfile.BadZipFile, Exception):
        return False


def is_valid_heic_heif(header: bytes) -> bool:
    """
    Validate HEIC/HEIF by checking for proper ftyp box with HEIC/HEIF brand codes.
    Prevents false positives from MP4, MOV, M4A which also use ftyp.
    """
    # ISO Base Media File Format: first 4 bytes = box size, next 4 bytes = 'ftyp'
    if len(header) < 12:
        return False
    
    # Check for ftyp box marker at bytes 4-7
    if header[4:8] != b'ftyp':
        return False
    
    # Major brand is at bytes 8-12
    major_brand = header[8:12]
    if major_brand in HEIC_HEIF_BRANDS:
        return True
    
    # Also check compatible brands (after major brand and version)
    # Compatible brands start at byte 16 and continue in 4-byte chunks
    if len(header) >= 20:
        for i in range(16, min(len(header), 64), 4):
            if i + 4 <= len(header):
                brand = header[i:i+4]
                if brand in HEIC_HEIF_BRANDS:
                    return True
    
    return False


def allowed_question_doc(filename):
    """Check if file extension is allowed for question documents."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in QUESTION_DOC_EXTENSIONS


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


# Allowed extensions for answer key (PDF and plain text)
ANSWER_KEY_EXTENSIONS = {'pdf', 'txt', 'md', 'markdown'}

def validate_answer_key(file):
    """Validate answer key file (PDF, TXT, or MD)."""
    errors = []
    
    if not file.filename:
        errors.append('Nama file tidak valid.')
        return errors
    
    ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    if ext not in ANSWER_KEY_EXTENSIONS:
        errors.append(f'File {file.filename} memiliki ekstensi tidak didukung. Gunakan PDF, TXT, atau MD.')
        return errors
    
    # Plain text files don't need strict validation
    if ext in {'txt', 'md', 'markdown'}:
        return errors
    
    # PDF validation
    if ext == 'pdf':
        if file.content_type not in ['application/pdf', 'application/x-pdf']:
            errors.append(f'File {file.filename} memiliki tipe MIME tidak valid: {file.content_type}')
        
        file.seek(0)
        header = file.read(5)
        file.seek(0)
        
        if header != b'%PDF-':
            errors.append(f'File {file.filename} bukan file PDF yang valid.')
    
    return errors


def validate_question_doc(file):
    """Validate question document file (PDF, DOCX, plain text, or image) with MIME and magic byte checks."""
    errors = []
    
    # Check filename extension
    if not file.filename:
        errors.append('Nama file tidak valid.')
        return errors
    
    if not allowed_question_doc(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
        errors.append(f'File {file.filename} memiliki ekstensi tidak didukung: .{ext}')
        return errors
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    
    # Plain text files don't need strict MIME/signature validation
    if ext in {'txt', 'md', 'markdown'}:
        return errors  # Allow plain text files without strict validation
    
    # Check MIME type
    mime_type = file.content_type or file.mimetype
    # Allow generic image/* for images, or check specific MIME types
    is_image_ext = ext in {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'heic', 'heif', 'tiff', 'tif'}
    mime_valid = (
        mime_type in QUESTION_DOC_MIME_TYPES or
        (is_image_ext and mime_type and mime_type.startswith('image/'))
    )
    if not mime_valid and mime_type:
        errors.append(f'File {file.filename} memiliki tipe MIME tidak valid: {mime_type}')
    
    # Check magic bytes (file signature)
    file.seek(0)
    header = file.read(64)  # Read more bytes for HEIC brand detection
    file.seek(0)  # Reset file pointer
    
    signature_valid = False
    
    if ext == 'pdf':
        signature_valid = header.startswith(FILE_SIGNATURES['pdf'])
    elif ext in {'jpg', 'jpeg'}:
        signature_valid = header.startswith(FILE_SIGNATURES['jpg'])
    elif ext == 'png':
        signature_valid = header.startswith(FILE_SIGNATURES['png'])
    elif ext == 'gif':
        signature_valid = header.startswith(FILE_SIGNATURES['gif'][0]) or header.startswith(FILE_SIGNATURES['gif'][1])
    elif ext == 'bmp':
        signature_valid = header.startswith(FILE_SIGNATURES['bmp'])
    elif ext in {'tiff', 'tif'}:
        signature_valid = header.startswith(FILE_SIGNATURES['tiff'][0]) or header.startswith(FILE_SIGNATURES['tiff'][1])
    elif ext == 'webp':
        signature_valid = header.startswith(FILE_SIGNATURES['webp']) and b'WEBP' in header[:12]
    elif ext == 'docx':
        # DOCX requires deep validation - check ZIP structure and Word-specific files
        if header.startswith(FILE_SIGNATURES['zip']):
            file.seek(0)
            file_content = file.read()
            file.seek(0)
            signature_valid = is_valid_docx(file_content)
        else:
            signature_valid = False
    elif ext == 'doc':
        signature_valid = header.startswith(FILE_SIGNATURES['doc'])
    elif ext in {'heic', 'heif'}:
        # HEIC/HEIF requires proper brand validation to distinguish from MP4/MOV
        signature_valid = is_valid_heic_heif(header)
    else:
        # Unknown extension - fail-safe: reject files without explicit signature handler
        # This prevents bypassing validation if new extensions are added without signature checks
        signature_valid = False
        errors.append(f'File {file.filename} memiliki ekstensi (.{ext}) yang belum memiliki validasi signature.')
        return errors
    
    if not signature_valid:
        errors.append(f'File {file.filename} memiliki signature tidak valid (kemungkinan file corrupt atau format tidak sesuai).')
    
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
        additional_notes = request.form.get('additional_notes', '').strip() or None
        question_text = request.form.get('question_text', '').strip() or None
        
        # Validate score range
        if score_min >= score_max:
            return jsonify({'success': False, 'error': 'Nilai minimum harus lebih kecil dari nilai maksimum.'}), 400
        
        if score_min < 0 or score_max > 100:
            return jsonify({'success': False, 'error': 'Rentang nilai harus antara 0 dan 100.'}), 400

        if question_text and len(question_text) > 10000:
            return jsonify({'success': False, 'error': 'Teks soal/tugas maksimal 10000 karakter.'}), 400
        
        # Validate active LLM provider configuration before accepting job uploads.
        provider_ready, provider_error = _validate_llm_provider_ready()
        if not provider_ready:
            return jsonify({'success': False, 'error': provider_error}), 400

        max_count = current_app.config['MAX_PDF_COUNT']
        max_file_size_bytes = int(current_app.config['MAX_FILE_SIZE_MB']) * 1024 * 1024

        # Get student files
        student_files = request.files.getlist('student_files')
        
        if not student_files or len(student_files) == 0:
            return jsonify({'success': False, 'error': 'Tidak ada file mahasiswa yang diunggah.'}), 400
        
        # Check file count limit
        if len(student_files) > max_count:
            return jsonify({'success': False, 'error': f'Jumlah file melebihi batas maksimum ({max_count} file).'}), 400

        # Check configured file-size limit per uploaded student file
        for file in student_files:
            if file and file.filename:
                size_error = _validate_file_size(file, max_file_size_bytes, 'File')
                if size_error:
                    return jsonify({'success': False, 'error': size_error}), 400
        
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
        
        # Handle answer key (optional - supports PDF, TXT, MD)
        answer_key_path = None
        answer_key_file = request.files.get('answer_key')
        if answer_key_file and answer_key_file.filename:
            size_error = _validate_file_size(answer_key_file, max_file_size_bytes, 'Kunci jawaban')
            if size_error:
                return jsonify({'success': False, 'error': size_error}), 400

            ak_errors = validate_answer_key(answer_key_file)
            if ak_errors:
                return jsonify({'success': False, 'error': f'Kunci jawaban tidak valid: {" ".join(ak_errors)}'}), 400
            
            ak_filename = secure_filename(answer_key_file.filename)
            answer_key_path = os.path.join(job_folder, f"answer_key_{ak_filename}")
            answer_key_file.save(answer_key_path)
        
        # Handle question documents (optional, up to 10 files)
        question_doc_paths_list = []
        question_files_raw = request.files.getlist('question_documents')
        
        # Filter out empty FileStorage entries
        question_files = []
        for qf in question_files_raw:
            if qf and qf.filename and qf.filename.strip():
                size = _file_size_bytes(qf)
                if size > 0:
                    question_files.append(qf)
        
        if question_files:
            # Check maximum 10 files (after filtering)
            if len(question_files) > 10:
                return jsonify({'success': False, 'error': 'Maksimal 10 file dokumen soal yang diperbolehkan.'}), 400
            
            # Validate all files first before creating folder
            for qfile in question_files:
                size_error = _validate_file_size(qfile, max_file_size_bytes, 'Dokumen soal')
                if size_error:
                    return jsonify({'success': False, 'error': size_error}), 400

                q_errors = validate_question_doc(qfile)
                if q_errors:
                    return jsonify({'success': False, 'error': f'Dokumen soal tidak valid: {" ".join(q_errors)}'}), 400
            
            # Create folder only after all validations pass
            question_folder = os.path.join(job_folder, 'questions')
            os.makedirs(question_folder, exist_ok=True)
            
            try:
                for qfile in question_files:
                    q_filename = secure_filename(qfile.filename)
                    unique_q_filename = f"{uuid.uuid4().hex[:8]}_{q_filename}"
                    q_filepath = os.path.join(question_folder, unique_q_filename)
                    qfile.save(q_filepath)
                    question_doc_paths_list.append(q_filepath)
            except Exception as save_error:
                # Cleanup already saved files on error
                for saved_path in question_doc_paths_list:
                    try:
                        if os.path.exists(saved_path):
                            os.remove(saved_path)
                    except:
                        pass
                # Remove question folder if empty
                try:
                    if os.path.exists(question_folder) and not os.listdir(question_folder):
                        os.rmdir(question_folder)
                except:
                    pass
                return jsonify({'success': False, 'error': f'Gagal menyimpan dokumen soal: {str(save_error)}'}), 500
        
        # Convert question doc paths to JSON string for storage
        question_doc_paths_json = json.dumps(question_doc_paths_list) if question_doc_paths_list else None
        
        # Validate at least one reference is provided
        has_answer_key = answer_key_path is not None
        has_question_docs = len(question_doc_paths_list) > 0
        has_question_text = question_text is not None
        has_additional_notes = additional_notes is not None and len(additional_notes.strip()) > 0
        
        if not has_answer_key and not has_question_docs and not has_question_text and not has_additional_notes:
            return jsonify({'success': False, 'error': 'Minimal satu referensi harus diisi: Kunci Jawaban, Dokumen Soal/Tugas, Teks Soal/Tugas, atau Catatan Tambahan.'}), 400
        
        # Create job in database
        job = Job(
            user_id=current_user.id,
            score_min=score_min,
            score_max=score_max,
            enable_evaluation=enable_evaluation,
            answer_key_path=answer_key_path,
            question_doc_paths=question_doc_paths_json,
            question_text=question_text,
            additional_notes=additional_notes,
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
        
    except RequestEntityTooLarge:
        max_mb = int(current_app.config.get('MAX_FILE_SIZE_MB', 10))
        return jsonify({
            'success': False,
            'error': f'Total ukuran upload melebihi batas maksimum request ({max_mb} MB).'
        }), 413
    except Exception as e:
        current_app.logger.error(f'Error upload: {str(e)}')
        SystemLog.log('ERROR', 'upload', f'Error upload: {str(e)}', user_id=current_user.id)
        return jsonify({'success': False, 'error': f'Terjadi kesalahan: {str(e)}'}), 500


@dashboard_bp.route('/api/upload-single', methods=['POST'])
@login_required
def upload_single():
    """Handle single processing upload - one student at a time with multiple files per student."""
    try:
        # Get form data
        score_min = int(request.form.get('score_min', current_app.config['DEFAULT_SCORE_MIN']))
        score_max = int(request.form.get('score_max', current_app.config['DEFAULT_SCORE_MAX']))
        enable_evaluation = request.form.get('enable_evaluation', 'true').lower() == 'true'
        additional_notes = request.form.get('additional_notes', '').strip() or None
        question_text = request.form.get('question_text', '').strip() or None
        
        # Validate score range
        if score_min >= score_max:
            return jsonify({'success': False, 'error': 'Nilai minimum harus lebih kecil dari nilai maksimum.'}), 400
        
        if score_min < 0 or score_max > 100:
            return jsonify({'success': False, 'error': 'Rentang nilai harus antara 0 dan 100.'}), 400

        if question_text and len(question_text) > 10000:
            return jsonify({'success': False, 'error': 'Teks soal/tugas maksimal 10000 karakter.'}), 400
        
        # Validate active LLM provider configuration before accepting job uploads.
        provider_ready, provider_error = _validate_llm_provider_ready()
        if not provider_ready:
            return jsonify({'success': False, 'error': provider_error}), 400

        max_count = current_app.config['MAX_PDF_COUNT']
        max_file_size_bytes = int(current_app.config['MAX_FILE_SIZE_MB']) * 1024 * 1024

        # Get students data
        students_data_str = request.form.get('students_data', '[]')
        try:
            students_data = json.loads(students_data_str)
        except json.JSONDecodeError:
            return jsonify({'success': False, 'error': 'Data mahasiswa tidak valid.'}), 400
        
        if not students_data or len(students_data) == 0:
            return jsonify({'success': False, 'error': 'Tidak ada data mahasiswa.'}), 400

        total_answer_files = 0
        for student_index in range(len(students_data)):
            student_files = request.files.getlist(f'student_{student_index}_files')
            total_answer_files += len([
                file for file in student_files
                if file and file.filename and file.filename.strip()
            ])

        if total_answer_files > max_count:
            return jsonify({'success': False, 'error': f'Jumlah file melebihi batas maksimum ({max_count} file).'}), 400

        # Create job folder
        job_id = str(uuid.uuid4())
        job_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], job_id)
        os.makedirs(job_folder, exist_ok=True)
        
        # Handle answer key (optional - supports PDF, TXT, MD)
        answer_key_path = None
        answer_key_file = request.files.get('answer_key')
        if answer_key_file and answer_key_file.filename:
            size_error = _validate_file_size(answer_key_file, max_file_size_bytes, 'Kunci jawaban')
            if size_error:
                return jsonify({'success': False, 'error': size_error}), 400

            ak_errors = validate_answer_key(answer_key_file)
            if ak_errors:
                return jsonify({'success': False, 'error': f'Kunci jawaban tidak valid: {" ".join(ak_errors)}'}), 400
            
            ak_filename = secure_filename(answer_key_file.filename)
            answer_key_path = os.path.join(job_folder, f"answer_key_{ak_filename}")
            answer_key_file.save(answer_key_path)
        
        # Handle question documents (optional, up to 10 files)
        question_doc_paths_list = []
        question_files_raw = request.files.getlist('question_documents')
        
        question_files = []
        for qf in question_files_raw:
            if qf and qf.filename and qf.filename.strip():
                size = _file_size_bytes(qf)
                if size > 0:
                    question_files.append(qf)
        
        if question_files:
            if len(question_files) > 10:
                return jsonify({'success': False, 'error': 'Maksimal 10 file dokumen soal yang diperbolehkan.'}), 400
            
            for qfile in question_files:
                size_error = _validate_file_size(qfile, max_file_size_bytes, 'Dokumen soal')
                if size_error:
                    return jsonify({'success': False, 'error': size_error}), 400

                q_errors = validate_question_doc(qfile)
                if q_errors:
                    return jsonify({'success': False, 'error': f'Dokumen soal tidak valid: {" ".join(q_errors)}'}), 400
            
            question_folder = os.path.join(job_folder, 'questions')
            os.makedirs(question_folder, exist_ok=True)
            
            for qfile in question_files:
                q_filename = secure_filename(qfile.filename)
                unique_q_filename = f"{uuid.uuid4().hex[:8]}_{q_filename}"
                q_filepath = os.path.join(question_folder, unique_q_filename)
                qfile.save(q_filepath)
                question_doc_paths_list.append(q_filepath)
        
        question_doc_paths_json = json.dumps(question_doc_paths_list) if question_doc_paths_list else None
        
        # Process each student
        saved_files = []
        student_folder = os.path.join(job_folder, 'students')
        os.makedirs(student_folder, exist_ok=True)
        
        for student_index, student in enumerate(students_data):
            # Students no longer provide NIM/name manually, LLM will extract it
            # Get files for this student
            student_files = request.files.getlist(f'student_{student_index}_files')
            non_empty_student_files = [
                file for file in student_files
                if file and file.filename and file.filename.strip()
            ]
            
            if not non_empty_student_files:
                return jsonify({'success': False, 'error': f'Tidak ada file untuk mahasiswa nomor {student_index + 1}.'}), 400
            
            # Create student subfolder
            student_subfolder = os.path.join(student_folder, f"{student_index}")
            os.makedirs(student_subfolder, exist_ok=True)
            
            # Validate and save student files
            student_file_paths = []
            source_filename = None
            for file in non_empty_student_files:
                size_error = _validate_file_size(file, max_file_size_bytes, 'File jawaban')
                if size_error:
                    return jsonify({'success': False, 'error': size_error}), 400

                # Validate file
                q_errors = validate_question_doc(file)
                if q_errors:
                    return jsonify({'success': False, 'error': f'File jawaban tidak valid untuk mahasiswa nomor {student_index + 1}: {" ".join(q_errors)}'}), 400
                
                filename = secure_filename(file.filename)
                if source_filename is None:
                    source_filename = file.filename
                unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
                filepath = os.path.join(student_subfolder, unique_filename)
                file.save(filepath)
                student_file_paths.append(filepath)
            
            if not student_file_paths:
                return jsonify({'success': False, 'error': f'Tidak ada file valid untuk mahasiswa nomor {student_index + 1}.'}), 400
            
            # Store student info with file paths
            # NIM and name will be extracted by LLM from the files
            saved_files.append({
                'original_name': f"Mahasiswa_{student_index + 1}",
                'saved_name': f"{student_index}",
                'path': student_subfolder,
                'source_filename': source_filename or f"Mahasiswa_{student_index + 1}",
                'file_paths': student_file_paths,
                'is_single_processing': True
            })
        
        # Validate at least one reference is provided
        has_answer_key = answer_key_path is not None
        has_question_docs = len(question_doc_paths_list) > 0
        has_question_text = question_text is not None
        has_additional_notes = additional_notes is not None and len(additional_notes.strip()) > 0
        
        if not has_answer_key and not has_question_docs and not has_question_text and not has_additional_notes:
            return jsonify({'success': False, 'error': 'Minimal satu referensi harus diisi: Kunci Jawaban, Dokumen Soal/Tugas, Teks Soal/Tugas, atau Catatan Tambahan.'}), 400
        
        # Create job in database
        job = Job(
            user_id=current_user.id,
            score_min=score_min,
            score_max=score_max,
            enable_evaluation=enable_evaluation,
            answer_key_path=answer_key_path,
            question_doc_paths=question_doc_paths_json,
            question_text=question_text,
            additional_notes=additional_notes,
            total_files=len(saved_files),
            status='pending',
            job_type='single'
        )
        db.session.add(job)
        db.session.commit()
        
        # Create job results for each student (NIM and name will be filled by LLM later)
        for file_info in saved_files:
            result = JobResult(
                job_id=job.id,
                filename=file_info['original_name'],
                status='pending'
            )
            db.session.add(result)
        db.session.commit()
        
        # Log upload
        current_app.logger.info(f'Single Upload: {len(saved_files)} mahasiswa oleh {current_user.username}')
        SystemLog.log('INFO', 'upload_single', 
                     f'Upload single processing {len(saved_files)} mahasiswa', 
                     user_id=current_user.id,
                     details=json.dumps({'job_id': job.id, 'student_count': len(saved_files)}))
        
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
            'message': f'Berhasil mengunggah data {len(saved_files)} mahasiswa. Proses penilaian dimulai.'
        })
        
    except RequestEntityTooLarge:
        max_mb = int(current_app.config.get('MAX_FILE_SIZE_MB', 10))
        return jsonify({
            'success': False,
            'error': f'Total ukuran upload melebihi batas maksimum request ({max_mb} MB).'
        }), 413
    except Exception as e:
        current_app.logger.error(f'Error single upload: {str(e)}')
        SystemLog.log('ERROR', 'upload_single', f'Error single upload: {str(e)}', user_id=current_user.id)
        return jsonify({'success': False, 'error': f'Terjadi kesalahan: {str(e)}'}), 500


@dashboard_bp.route('/api/progress/<int:job_id>')
@login_required
def get_progress(job_id):
    """Get job progress via Server-Sent Events (SSE)."""
    owned_job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
    if not owned_job:
        return jsonify({'success': False, 'error': 'Job tidak ditemukan.'}), 404

    def generate():
        """Generate SSE events."""
        import time
        
        while True:
            # Get progress from memory or database
            if job_id in job_progress:
                progress = job_progress[job_id]
            else:
                # Fallback to database
                job = Job.query.filter_by(id=job_id, user_id=current_user.id).first()
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
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


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
