"""
Authentication routes for AutoScoring application.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse, parse_qsl, urlencode
from werkzeug.routing import RequestRedirect

from app.extensions import db
from app.models import User, SystemLog, utc_now_naive

auth_bp = Blueprint('auth', __name__)


def _resolve_safe_next_endpoint(next_page: str):
    """Resolve a safe internal next endpoint from query param."""
    if not next_page:
        return None

    parsed = urlparse(next_page)
    if parsed.scheme or parsed.netloc:
        return None

    path = parsed.path
    if not path or not path.startswith('/') or path.startswith('//'):
        return None

    adapter = current_app.url_map.bind('')
    try:
        endpoint, values = adapter.match(path, method='GET')
    except RequestRedirect as exc:
        canonical = urlparse(exc.new_url)
        canonical_path = canonical.path
        if not canonical_path or not canonical_path.startswith('/') or canonical_path.startswith('//'):
            return None
        try:
            endpoint, values = adapter.match(canonical_path, method='GET')
        except Exception:
            return None
    except Exception:
        return None

    if endpoint in {'auth.login', 'auth.logout'}:
        return None

    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    return endpoint, values, query_items


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
            user.last_login = utc_now_naive()
            db.session.commit()
            
            current_app.logger.info(f'Login berhasil: {username}')
            SystemLog.log('INFO', 'login', f'Login berhasil: {username}', user_id=user.id)
            
            # Redirect to next page or dashboard
            safe_next = _resolve_safe_next_endpoint(request.args.get('next'))
            if safe_next:
                endpoint, values, query_items = safe_next
                target = url_for(endpoint, **values)
                if query_items:
                    target = f"{target}?{urlencode(query_items, doseq=True)}"
                return redirect(target)
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
