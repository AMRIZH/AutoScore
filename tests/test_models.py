"""
Unit tests for database models.
"""

import pytest
from datetime import datetime
from app.models import User, Job, JobResult, SystemLog


class TestUserModel:
    """Test User model."""
    
    def test_create_user(self, app):
        """Test creating a new user."""
        with app.app_context():
            from app.extensions import db
            
            user = User(username='newuser', role='aslab')
            user.set_password('securepass123')
            db.session.add(user)
            db.session.commit()
            
            assert user.id is not None
            assert user.username == 'newuser'
            assert user.role == 'aslab'
            assert user.check_password('securepass123')
            assert not user.check_password('wrongpass')
    
    def test_user_is_admin(self, app):
        """Test is_admin property."""
        with app.app_context():
            from app.extensions import db
            
            admin = User(username='admin_test', role='admin')
            admin.set_password('adminpass')
            db.session.add(admin)
            
            aslab = User(username='aslab_test', role='aslab')
            aslab.set_password('aslabpass')
            db.session.add(aslab)
            
            db.session.commit()
            
            assert admin.is_admin == True
            assert aslab.is_admin == False
    
    def test_user_repr(self, app):
        """Test User __repr__."""
        with app.app_context():
            user = User(username='reprtest', role='aslab')
            assert 'reprtest' in repr(user)


class TestJobModel:
    """Test Job model."""
    
    def test_create_job(self, app):
        """Test creating a new job."""
        with app.app_context():
            from app.extensions import db
            
            user = User.query.filter_by(username='testuser').first()
            
            job = Job(
                user_id=user.id,
                score_min=0,
                score_max=100,
                enable_evaluation=True,
                total_files=5,
                status='pending',
                job_type='bulk'
            )
            db.session.add(job)
            db.session.commit()
            
            assert job.id is not None
            assert job.user_id == user.id
            assert job.score_min == 0
            assert job.score_max == 100
            assert job.status == 'pending'
            assert job.job_type == 'bulk'
    
    def test_job_single_processing(self, app):
        """Test job with single processing type."""
        with app.app_context():
            from app.extensions import db
            
            user = User.query.filter_by(username='testuser').first()
            
            job = Job(
                user_id=user.id,
                score_min=40,
                score_max=100,
                total_files=3,
                status='pending',
                job_type='single'
            )
            db.session.add(job)
            db.session.commit()
            
            assert job.job_type == 'single'
    
    def test_job_with_additional_notes(self, app):
        """Test job with additional notes."""
        with app.app_context():
            from app.extensions import db
            
            user = User.query.filter_by(username='testuser').first()
            
            job = Job(
                user_id=user.id,
                score_min=0,
                score_max=100,
                total_files=1,
                additional_notes='Soal nomor 5 adalah bonus'
            )
            db.session.add(job)
            db.session.commit()
            
            assert job.additional_notes == 'Soal nomor 5 adalah bonus'


class TestJobResultModel:
    """Test JobResult model."""
    
    def test_create_job_result(self, app):
        """Test creating a job result."""
        with app.app_context():
            from app.extensions import db
            
            user = User.query.filter_by(username='testuser').first()
            
            job = Job(user_id=user.id, total_files=1)
            db.session.add(job)
            db.session.commit()
            
            result = JobResult(
                job_id=job.id,
                filename='test_student.pdf',
                nim='L200200001',
                student_name='John Doe',
                score=85,
                evaluation='Jawaban baik',
                status='completed'
            )
            db.session.add(result)
            db.session.commit()
            
            assert result.id is not None
            assert result.job_id == job.id
            assert result.nim == 'L200200001'
            assert result.student_name == 'John Doe'
            assert result.score == 85
    
    def test_job_result_without_nim_name(self, app):
        """Test job result without NIM and name (for Single Processing where LLM extracts)."""
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
            
            assert result.nim is None
            assert result.student_name is None
            assert result.status == 'pending'


class TestSystemLogModel:
    """Test SystemLog model."""
    
    def test_create_log(self, app):
        """Test creating a log entry."""
        with app.app_context():
            from app.extensions import db
            
            user = User.query.filter_by(username='testuser').first()
            
            log = SystemLog.log(
                level='INFO',
                category='test',
                message='Test log message',
                user_id=user.id
            )
            
            assert log.id is not None
            assert log.level == 'INFO'
            assert log.category == 'test'
            assert log.message == 'Test log message'
