"""
Unit tests for dashboard routes (Bulk & Single Processing).
"""

import pytest
import json
import io
from app.models import User, Job, JobResult
from app.models import LLMConfig


class TestDashboardAccess:
    """Test dashboard access and authentication."""
    
    def test_dashboard_requires_login(self, client):
        """Test that dashboard requires authentication."""
        response = client.get('/dashboard')
        assert response.status_code in [302, 401]  # Redirect to login or unauthorized
    
    def test_dashboard_accessible_when_logged_in(self, auth_client):
        """Test that logged in user can access dashboard."""
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Dashboard Penilaian' in response.data
    
    def test_dashboard_has_tabs(self, auth_client):
        """Test that dashboard has both Bulk and Single Processing tabs."""
        response = auth_client.get('/dashboard')
        assert response.status_code == 200
        assert b'Penilaian Massal' in response.data
        assert b'Penilaian Per Mahasiswa' in response.data

    def test_llm_readiness_requires_gemini_key(self, auth_client, app):
        """Readiness endpoint should fail when Gemini is active but key list is empty."""
        with app.app_context():
            LLMConfig.set('llm_provider', 'gemini')
            LLMConfig.set('gemini_api_keys', '[]')

        response = auth_client.get('/api/llm-readiness')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['ready'] is False
        assert 'GEMINI' in data['message']


class TestBulkProcessingUpload:
    """Test bulk processing upload endpoint."""
    
    def test_upload_requires_auth(self, client):
        """Test that upload requires authentication."""
        response = client.post('/api/upload')
        assert response.status_code in [302, 401]
    
    def test_upload_requires_files(self, auth_client):
        """Test that upload requires student files."""
        response = auth_client.post('/api/upload', data={
            'score_min': '40',
            'score_max': '100',
            'enable_evaluation': 'true'
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
    
    def test_upload_validates_score_range(self, auth_client, sample_pdf):
        """Test that upload validates score range."""
        with open(sample_pdf, 'rb') as f:
            response = auth_client.post('/api/upload', data={
                'student_files': (f, 'test.pdf'),
                'score_min': '100',  # Invalid: min > max
                'score_max': '50',
                'enable_evaluation': 'true'
            })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'minimum' in data['error'].lower() or 'maksimum' in data['error'].lower()
    
    def test_upload_with_valid_pdf(self, auth_client, sample_pdf, app):
        """Test upload with valid PDF file."""
        with open(sample_pdf, 'rb') as f:
            response = auth_client.post('/api/upload', 
                data={
                    'student_files': (f, 'test_student.pdf'),
                    'score_min': '40',
                    'score_max': '100',
                    'enable_evaluation': 'true',
                    'additional_notes': 'Test notes'
                },
                content_type='multipart/form-data'
            )
        
        # Should succeed or return job_id
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] == True
            assert 'job_id' in data

    def test_upload_accepts_plain_question_text_without_question_docs(self, auth_client, sample_pdf, app):
        """Bulk upload should accept direct question text as a valid reference."""
        with open(sample_pdf, 'rb') as f:
            response = auth_client.post('/api/upload',
                data={
                    'student_files': (f, 'test_student.pdf'),
                    'score_min': '40',
                    'score_max': '100',
                    'question_text': 'Jelaskan langkah-langkah analisis data dan berikan contoh output.'
                },
                content_type='multipart/form-data'
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        with app.app_context():
            from app.extensions import db
            job = db.session.get(Job, data['job_id'])
            assert job is not None
            assert 'analisis data' in (job.question_text or '').lower()

    def test_upload_blocked_when_provider_key_missing(self, auth_client, sample_pdf, app):
        """Bulk upload must be blocked if active provider requires API key but key is missing."""
        with app.app_context():
            LLMConfig.set('llm_provider', 'openai')
            LLMConfig.set('openai_api_key', '')

        with open(sample_pdf, 'rb') as f:
            response = auth_client.post('/api/upload', data={
                'student_files': (f, 'test_student.pdf'),
                'score_min': '40',
                'score_max': '100',
                'additional_notes': 'Test notes'
            }, content_type='multipart/form-data')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'api key' in data['error'].lower()

    def test_upload_rejects_question_text_over_limit(self, auth_client, sample_pdf):
        """Bulk upload should reject question_text above 10000 chars."""
        with open(sample_pdf, 'rb') as f:
            response = auth_client.post('/api/upload', data={
                'student_files': (f, 'test_student.pdf'),
                'score_min': '40',
                'score_max': '100',
                'question_text': 'a' * 10001,
            }, content_type='multipart/form-data')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert '10000' in data['error']

    def test_upload_blocked_when_github_key_missing(self, auth_client, sample_pdf, app):
        """Bulk upload must be blocked if GitHub provider key is missing."""
        with app.app_context():
            LLMConfig.set('llm_provider', 'github')
            LLMConfig.set('github_api_key', '')

        with open(sample_pdf, 'rb') as f:
            response = auth_client.post('/api/upload', data={
                'student_files': (f, 'test_student.pdf'),
                'score_min': '40',
                'score_max': '100',
                'additional_notes': 'Test notes'
            }, content_type='multipart/form-data')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'github' in data['error'].lower()


class TestSingleProcessingUpload:
    """Test single processing upload endpoint."""
    
    def test_single_upload_requires_auth(self, client):
        """Test that single upload requires authentication."""
        response = client.post('/api/upload-single')
        assert response.status_code in [302, 401]
    
    def test_single_upload_requires_students_data(self, auth_client):
        """Test that single upload requires students_data."""
        response = auth_client.post('/api/upload-single', data={
            'score_min': '40',
            'score_max': '100',
            'students_data': '[]'  # Empty array
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] == False
    
    def test_single_upload_validates_score_range(self, auth_client):
        """Test that single upload validates score range."""
        response = auth_client.post('/api/upload-single', data={
            'score_min': '100',
            'score_max': '50',  # Invalid range
            'students_data': json.dumps([{'fileCount': 1}])
        })
        assert response.status_code == 400
    
    def test_single_upload_requires_files_per_student(self, auth_client):
        """Test that each student needs files."""
        response = auth_client.post('/api/upload-single', data={
            'score_min': '40',
            'score_max': '100',
            'students_data': json.dumps([{'fileCount': 1}])
            # No actual files provided for student_0_files
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'file' in data['error'].lower()
    
    def test_single_upload_with_image(self, auth_client, sample_image, app):
        """Test single upload with image file."""
        with open(sample_image, 'rb') as f:
            response = auth_client.post('/api/upload-single',
                data={
                    'score_min': '40',
                    'score_max': '100',
                    'enable_evaluation': 'true',
                    'students_data': json.dumps([{'fileCount': 1}]),
                    'student_0_files': (f, 'answer.png'),
                    'additional_notes': 'Test notes'
                },
                content_type='multipart/form-data'
            )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] == True
            assert 'job_id' in data

    def test_single_upload_accepts_plain_question_text_without_question_docs(self, auth_client, sample_image, app):
        """Single upload should accept direct question text as a valid reference."""
        with open(sample_image, 'rb') as f:
            response = auth_client.post('/api/upload-single',
                data={
                    'score_min': '40',
                    'score_max': '100',
                    'students_data': json.dumps([{'fileCount': 1}]),
                    'student_0_files': (f, 'answer.png'),
                    'question_text': 'Tuliskan jawaban untuk soal algoritma sorting berikut.'
                },
                content_type='multipart/form-data'
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        with app.app_context():
            from app.extensions import db
            job = db.session.get(Job, data['job_id'])
            assert job is not None
            assert 'algoritma sorting' in (job.question_text or '').lower()

    def test_single_upload_blocked_when_provider_key_missing(self, auth_client, sample_image, app):
        """Single upload must be blocked if active provider requires API key but key is missing."""
        with app.app_context():
            LLMConfig.set('llm_provider', 'deepseek')
            LLMConfig.set('deepseek_api_key', '')

        with open(sample_image, 'rb') as f:
            response = auth_client.post('/api/upload-single', data={
                'score_min': '40',
                'score_max': '100',
                'students_data': json.dumps([{'fileCount': 1}]),
                'student_0_files': (f, 'answer.png'),
                'additional_notes': 'Test notes'
            }, content_type='multipart/form-data')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'api key' in data['error'].lower()

    def test_single_upload_rejects_question_text_over_limit(self, auth_client, sample_image):
        """Single upload should reject question_text above 10000 chars."""
        with open(sample_image, 'rb') as f:
            response = auth_client.post('/api/upload-single', data={
                'score_min': '40',
                'score_max': '100',
                'students_data': json.dumps([{'fileCount': 1}]),
                'student_0_files': (f, 'answer.png'),
                'question_text': 'a' * 10001,
            }, content_type='multipart/form-data')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert '10000' in data['error']


class TestJobStatusEndpoints:
    """Test job status endpoints."""
    
    def test_job_status_requires_auth(self, client):
        """Test that job status requires authentication."""
        response = client.get('/api/job/1')
        assert response.status_code in [302, 401]
    
    def test_job_status_not_found(self, auth_client):
        """Test job status for non-existent job."""
        response = auth_client.get('/api/job/99999')
        assert response.status_code == 404
    
    def test_download_requires_auth(self, client):
        """Test that download requires authentication."""
        response = client.get('/api/download/1')
        assert response.status_code in [302, 401]

    def test_progress_fallback_uses_database_state(self, auth_client, app):
        """Progress endpoint should fall back to DB state when in-memory progress is unavailable."""
        with app.app_context():
            from app.extensions import db
            from app.routes.dashboard import job_progress

            user = User.query.filter_by(username='testuser').first()
            job = Job(
                user_id=user.id,
                status='completed',
                status_message='Selesai dari DB',
                total_files=2,
                processed_files=2,
                job_type='single',
            )
            db.session.add(job)
            db.session.commit()

            job_progress.pop(job.id, None)

        response = auth_client.get(f'/api/progress/{job.id}')
        assert response.status_code == 200
        body = response.data.decode('utf-8')
        first_event = next((line for line in body.splitlines() if line.startswith('data: ')), None)
        assert first_event is not None
        payload = json.loads(first_event[len('data: '):])
        assert payload['status'] == 'completed'
        assert payload['message'] == 'Selesai dari DB'

    def test_progress_rejects_other_user_job(self, client, app):
        """Progress endpoint must not expose jobs belonging to another user."""
        with app.app_context():
            from app.extensions import db

            user_a = User.query.filter_by(username='testuser').first()
            user_b = User(username='otheradmin', role='admin')
            user_b.set_password('otherpassword')
            db.session.add(user_b)
            db.session.commit()

            foreign_job = Job(
                user_id=user_a.id,
                status='processing',
                total_files=1,
                processed_files=0,
                job_type='single',
            )
            db.session.add(foreign_job)
            db.session.commit()
            foreign_job_id = foreign_job.id

        client.post('/login', data={
            'username': 'otheradmin',
            'password': 'otherpassword'
        }, follow_redirects=True)

        response = client.get(f'/api/progress/{foreign_job_id}')
        assert response.status_code == 404


class TestFileValidation:
    """Test file validation functions."""
    
    def test_pdf_validation(self, auth_client, sample_pdf):
        """Test PDF file validation."""
        with open(sample_pdf, 'rb') as f:
            response = auth_client.post('/api/upload',
                data={
                    'student_files': (f, 'valid.pdf'),
                    'score_min': '40',
                    'score_max': '100',
                    'additional_notes': 'Test notes'
                },
                content_type='multipart/form-data'
            )
        # Should not fail on PDF validation
        if response.status_code == 400:
            data = json.loads(response.data)
            # Should not be a "bukan PDF" error for valid PDF
            assert 'bukan' not in data.get('error', '').lower() or 'pdf' not in data.get('error', '').lower()
    
    def test_image_validation(self, auth_client, sample_image):
        """Test image file validation for question docs."""
        with open(sample_image, 'rb') as f:
            response = auth_client.post('/api/upload-single',
                data={
                    'score_min': '40',
                    'score_max': '100',
                    'students_data': json.dumps([{'fileCount': 1}]),
                    'student_0_files': (f, 'answer.png'),
                    'additional_notes': 'Test notes'
                },
                content_type='multipart/form-data'
            )
        # PNG should be accepted
        if response.status_code == 400:
            data = json.loads(response.data)
            # Should not be a file type error
            assert 'ekstensi' not in data.get('error', '').lower()
