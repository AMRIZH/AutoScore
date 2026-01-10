"""
Authentication routes for AutoScoring application.
"""

from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, SystemLog

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        # Validate input
        if not username or not password:
            flash('Username dan password harus diisi.', 'danger')
            SystemLog.log('WARNING', 'login', f'Percobaan login gagal: input kosong', details=f'username: {username}')
            return render_template('login.html')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Successful login
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            current_app.logger.info(f'Login berhasil: {username}')
            SystemLog.log('INFO', 'login', f'Login berhasil: {username}', user_id=user.id)
            
            # Redirect to next page or dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.index'))
        else:
            # Failed login
            current_app.logger.warning(f'Login gagal: {username}')
            SystemLog.log('WARNING', 'login', f'Login gagal: username atau password salah', details=f'username: {username}')
            flash('Username atau password salah.', 'danger')
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user."""
    username = current_user.username
    user_id = current_user.id
    
    logout_user()
    
    current_app.logger.info(f'Logout: {username}')
    SystemLog.log('INFO', 'login', f'Logout: {username}', user_id=user_id)
    
    flash('Anda telah berhasil logout.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/')
def index():
    """Root URL redirects to login or dashboard."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return redirect(url_for('auth.login'))
