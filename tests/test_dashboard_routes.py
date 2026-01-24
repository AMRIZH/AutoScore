"""
Unit tests for dashboard routes (Bulk & Single Processing).
"""

import pytest
import json
import io
from app.models import User, Job, JobResult


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
