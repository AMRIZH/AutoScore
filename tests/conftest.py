"""
Konfigurasi untuk unit tests AutoScoring.
"""

import os
import sys
import tempfile

# Add parent directory to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture(scope='function')
def app():
    """Create application for testing."""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    
    # Set environment to disable scheduler before creating app
    os.environ['FLASK_TESTING'] = '1'
    
    app = create_app()
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'UPLOAD_FOLDER': tempfile.mkdtemp(),
        'RESULTS_FOLDER': tempfile.mkdtemp(),
        'SERVER_NAME': 'localhost',
    })
    
    # Stop scheduler if it's running
    try:
        if hasattr(app, 'extensions') and 'scheduler' in app.extensions:
            scheduler = app.extensions['scheduler']
            if scheduler.running:
                scheduler.shutdown(wait=False)
    except Exception:
        pass
    
    with app.app_context():
        db.create_all()
        
        # Create test user
        test_user = User(username='testuser', role='admin')
        test_user.set_password('testpassword')
        db.session.add(test_user)
        db.session.commit()
    
    yield app
    
    # Cleanup
    try:
        os.close(db_fd)
        os.unlink(db_path)
    except Exception:
        pass
    
    # Clear environment
    os.environ.pop('FLASK_TESTING', None)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()


@pytest.fixture
def auth_client(client, app):
    """Create authenticated test client."""
    with app.app_context():
        # Login
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=True)
    return client


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF file for testing."""
    pdf_content = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n115\n%%EOF'
    pdf_path = tmp_path / "test_student.pdf"
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def sample_image(tmp_path):
    """Create a sample image file for testing."""
    # Minimal valid PNG
    png_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
    img_path = tmp_path / "test_answer.png"
    img_path.write_bytes(png_content)
    return img_path
