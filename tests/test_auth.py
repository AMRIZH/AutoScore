"""
Unit tests for authentication routes.
"""

import pytest
from app.models import User


class TestLogin:
    """Test login functionality."""
    
    def test_login_page_loads(self, client):
        """Test that login page loads correctly."""
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Masuk' in response.data or b'Login' in response.data
    
    def test_login_with_valid_credentials(self, client, app):
        """Test login with valid credentials."""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        # Should redirect to dashboard
        assert b'Dashboard' in response.data or b'dashboard' in response.data.lower()

        with app.app_context():
            user = User.query.filter_by(username='testuser').first()
            assert user.last_login is not None
            # Stored timestamps are UTC-naive for DateTime columns without timezone=True.
            assert user.last_login.tzinfo is None
    
    def test_login_with_invalid_password(self, client):
        """Test login with invalid password."""
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        
        # Should show error or stay on login page
        assert b'salah' in response.data.lower() or b'invalid' in response.data.lower() or b'Masuk' in response.data
    
    def test_login_with_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'anypassword'
        }, follow_redirects=True)
        
        # Should show error or stay on login page
        assert response.status_code == 200


class TestLogout:
    """Test logout functionality."""
    
    def test_logout_redirects_to_login(self, auth_client):
        """Test that logout redirects to login page."""
        response = auth_client.get('/logout', follow_redirects=True)
        assert response.status_code == 200
        # Should be on login page or home
        assert b'Masuk' in response.data or b'Login' in response.data
    
    def test_cannot_access_dashboard_after_logout(self, auth_client):
        """Test that dashboard is not accessible after logout."""
        # First logout
        auth_client.get('/logout')
        
        # Try to access dashboard
        response = auth_client.get('/dashboard')
        assert response.status_code in [302, 401]  # Should redirect to login
