"""
Simple test to verify test setup works.
Works both as standalone script and with pytest.
"""

import os
import sys
import tempfile
import pytest

# Add parent directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set testing environment
os.environ['FLASK_TESTING'] = '1'


@pytest.fixture
def test_app():
    """Create a test app."""
    from app import create_app
    from app.extensions import db
    
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    test_config = {
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'TESTING': True,
        'WTF_CSRF_ENABLED': False
    }
    
    app = create_app(test_config=test_config)
    
    with app.app_context():
        db.create_all()
    
    yield app
    
    # Cleanup
    try:
        os.close(db_fd)
        os.unlink(db_path)
    except:
        pass


class TestAppCreation:
    """Test app creation."""
    
    def test_app_can_be_created(self, test_app):
        """Test that app can be created."""
        assert test_app is not None
        assert test_app.config['TESTING'] is True


class TestDatabase:
    """Test database operations."""
    
    def test_user_creation(self, test_app):
        """Test that users can be created."""
        from app.extensions import db
        from app.models import User
        
        with test_app.app_context():
            user = User(username='testuser_simple', role='admin')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
            
            found = User.query.filter_by(username='testuser_simple').first()
            assert found is not None
            assert found.check_password('testpass')
    
    def test_job_with_job_type(self, test_app):
        """Test Job model with job_type field."""
        from app.extensions import db
        from app.models import User, Job
        
        with test_app.app_context():
            # Create user
            user = User(username='job_test_user', role='admin')
            user.set_password('test')
            db.session.add(user)
            db.session.commit()
            
            # Create bulk job
            bulk_job = Job(
                user_id=user.id,
                score_min=40,
                score_max=100,
                total_files=5,
                job_type='bulk'
            )
            db.session.add(bulk_job)
            
            # Create single processing job
            single_job = Job(
                user_id=user.id,
                score_min=0,
                score_max=100,
                total_files=3,
                job_type='single'
            )
            db.session.add(single_job)
            db.session.commit()
            
            # Verify
            assert bulk_job.job_type == 'bulk'
            assert single_job.job_type == 'single'
    
    def test_job_result_without_nim_name(self, test_app):
        """Test JobResult without NIM/Name for Single Processing."""
        from app.extensions import db
        from app.models import User, Job, JobResult
        
        with test_app.app_context():
            user = User(username='result_test_user', role='admin')
            user.set_password('test')
            db.session.add(user)
            db.session.commit()
            
            job = Job(
                user_id=user.id,
                total_files=1,
                job_type='single'
            )
            db.session.add(job)
            db.session.commit()
            
            # Create result without NIM/Name
            result = JobResult(
                job_id=job.id,
                filename='Mahasiswa_1',
                status='pending'
            )
            db.session.add(result)
            db.session.commit()
            
            # Verify
            assert result.nim is None
            assert result.student_name is None
            assert result.status == 'pending'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
