"""
Integration tests for Single Processing feature.
"""

import pytest
import json
import io
from app.models import User, Job, JobResult


class TestSingleProcessingIntegration:
    """Integration tests for the Single Processing feature."""
    
    def test_single_processing_without_nim_name(self, auth_client, sample_image, app):
        """Test that Single Processing works without manual NIM/Name input."""
        with open(sample_image, 'rb') as f:
            response = auth_client.post('/api/upload-single',
                data={
                    'score_min': '40',
                    'score_max': '100',
                    'enable_evaluation': 'true',
                    'students_data': json.dumps([{'fileCount': 1}]),
                    'student_0_files': (f, 'jawaban_halaman1.png')
                },
                content_type='multipart/form-data'
            )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] == True
            
            # Verify job was created with 'single' type
            with app.app_context():
                from app.extensions import db
                job = Job.query.get(data['job_id'])
                assert job is not None
                assert job.job_type == 'single'
    
    def test_single_processing_multiple_files_per_student(self, auth_client, sample_image, app, tmp_path):
        """Test uploading multiple files for a single student."""
        # Create second image
        png2 = tmp_path / "page2.png"
        png2.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
        
        with open(sample_image, 'rb') as f1, open(png2, 'rb') as f2:
            response = auth_client.post('/api/upload-single',
                data={
                    'score_min': '40',
                    'score_max': '100',
                    'enable_evaluation': 'true',
                    'students_data': json.dumps([{'fileCount': 2}]),
                    'student_0_files': [(f1, 'page1.png'), (f2, 'page2.png')]
                },
                content_type='multipart/form-data'
            )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] == True
    
    def test_single_processing_multiple_students(self, auth_client, sample_image, app, tmp_path):
        """Test uploading files for multiple students."""
        # Create images for two students
        img1 = tmp_path / "student1.png"
        img1.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
        img2 = tmp_path / "student2.png"
        img2.write_bytes(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82')
        
        with open(img1, 'rb') as f1, open(img2, 'rb') as f2:
            response = auth_client.post('/api/upload-single',
                data={
                    'score_min': '40',
                    'score_max': '100',
                    'students_data': json.dumps([{'fileCount': 1}, {'fileCount': 1}]),
                    'student_0_files': (f1, 'student1.png'),
                    'student_1_files': (f2, 'student2.png')
                },
                content_type='multipart/form-data'
            )
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['success'] == True
            
            # Verify 2 job results were created
            with app.app_context():
                from app.extensions import db
                job = Job.query.get(data['job_id'])
                assert job.total_files == 2


class TestSingleProcessingJobResults:
    """Test JobResult handling for Single Processing."""
    
    def test_job_result_created_without_nim_name(self, app):
        """Test that JobResult for single processing is created without NIM/Name."""
        with app.app_context():
            from app.extensions import db
            
            user = User.query.filter_by(username='testuser').first()
            
            # Create single processing job
            job = Job(
                user_id=user.id,
                score_min=40,
                score_max=100,
                total_files=1,
                job_type='single'
            )
            db.session.add(job)
            db.session.commit()
            
            # Create job result without NIM/Name (LLM will fill later)
            result = JobResult(
                job_id=job.id,
                filename='Mahasiswa_1',
                status='pending'
            )
            db.session.add(result)
            db.session.commit()
            
            # Verify
            saved_result = JobResult.query.filter_by(job_id=job.id).first()
            assert saved_result.nim is None
            assert saved_result.student_name is None
            assert saved_result.filename == 'Mahasiswa_1'
    
    def test_job_result_updated_by_llm(self, app):
        """Test that JobResult can be updated with LLM-extracted NIM/Name."""
        with app.app_context():
            from app.extensions import db
            
            user = User.query.filter_by(username='testuser').first()
            
            job = Job(user_id=user.id, total_files=1, job_type='single')
            db.session.add(job)
            db.session.commit()
            
            result = JobResult(
                job_id=job.id,
                filename='Mahasiswa_1',
                status='pending'
            )
            db.session.add(result)
            db.session.commit()
            
            # Simulate LLM updating the result
            result.nim = 'L200200001'
            result.student_name = 'Ahmad Fauzi'
            result.score = 85
            result.evaluation = 'Jawaban bagus'
            result.status = 'completed'
            db.session.commit()
            
            # Verify update
            updated = JobResult.query.get(result.id)
            assert updated.nim == 'L200200001'
            assert updated.student_name == 'Ahmad Fauzi'
            assert updated.score == 85
