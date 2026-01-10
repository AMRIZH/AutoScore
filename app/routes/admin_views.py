"""
Flask-Admin views for AutoScoring application.
"""

from flask import redirect, url_for, request, flash
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from wtforms import PasswordField
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import User, Job, JobResult, SystemLog


class SecureAdminIndexView(AdminIndexView):
    """Secure admin index view - only accessible by admin users."""
    
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Anda tidak memiliki akses ke halaman admin.', 'danger')
            return redirect(url_for('auth.login'))
        
        # Get system info
        from flask import current_app
        system_info = {
            'gpu_available': current_app.config.get('GPU_AVAILABLE', False),
            'gpu_name': current_app.config.get('GPU_NAME', 'N/A'),
            'max_pdf_count': current_app.config.get('MAX_PDF_COUNT', 50),
            'enable_cleanup': current_app.config.get('ENABLE_CLEANUP', True),
            'enable_ocr': current_app.config.get('ENABLE_OCR', True),
            'max_workers': current_app.config.get('MAX_WORKERS', 4)
        }
        
        # Get statistics
        stats = {
            'total_users': User.query.count(),
            'total_jobs': Job.query.count(),
            'completed_jobs': Job.query.filter_by(status='completed').count(),
            'failed_jobs': Job.query.filter_by(status='failed').count()
        }
        
        return self.render('admin/custom_index.html', system_info=system_info, stats=stats)
    
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name, **kwargs):
        flash('Anda tidak memiliki akses ke halaman admin.', 'danger')
        return redirect(url_for('auth.login', next=request.url))


class SecureModelView(ModelView):
    """Base secure model view - only accessible by admin users."""
    
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name, **kwargs):
        flash('Anda tidak memiliki akses ke halaman admin.', 'danger')
        return redirect(url_for('auth.login', next=request.url))


class UserModelView(SecureModelView):
    """Admin view for User model with password management."""
    
    # Column settings
    column_list = ['id', 'username', 'role', 'created_at', 'last_login']
    column_searchable_list = ['username']
    column_filters = ['role', 'created_at']
    column_sortable_list = ['id', 'username', 'role', 'created_at', 'last_login']
    
    # Form settings
    form_columns = ['username', 'role', 'password']
    form_extra_fields = {
        'password': PasswordField('Password Baru')
    }
    
    # Display labels in Indonesian
    column_labels = {
        'id': 'ID',
        'username': 'Username',
        'role': 'Peran',
        'created_at': 'Dibuat',
        'last_login': 'Login Terakhir'
    }
    
    form_choices = {
        'role': [
            ('admin', 'Admin'),
            ('aslab', 'Asisten Lab')
        ]
    }
    
    def on_model_change(self, form, model, is_created):
        """Handle password hashing when creating/updating user."""
        if form.password.data:
            model.password_hash = generate_password_hash(form.password.data)


class JobModelView(SecureModelView):
    """Admin view for Job model."""
    
    # Column settings
    column_list = ['id', 'user', 'status', 'total_files', 'processed_files', 'created_at', 'completed_at']
    column_searchable_list = ['status']
    column_filters = ['status', 'created_at', 'user_id']
    column_sortable_list = ['id', 'status', 'total_files', 'created_at', 'completed_at']
    
    # Display labels in Indonesian
    column_labels = {
        'id': 'ID',
        'user': 'Pengguna',
        'status': 'Status',
        'total_files': 'Total File',
        'processed_files': 'File Diproses',
        'created_at': 'Dibuat',
        'completed_at': 'Selesai'
    }
    
    # Read-only (jobs shouldn't be manually created/edited)
    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True


class JobResultModelView(SecureModelView):
    """Admin view for JobResult model."""
    
    # Column settings
    column_list = ['id', 'job_id', 'filename', 'nim', 'student_name', 'score', 'status']
    column_searchable_list = ['nim', 'student_name', 'filename']
    column_filters = ['status', 'score', 'job_id']
    column_sortable_list = ['id', 'job_id', 'score', 'status']
    
    # Display labels in Indonesian
    column_labels = {
        'id': 'ID',
        'job_id': 'ID Job',
        'filename': 'Nama File',
        'nim': 'NIM',
        'student_name': 'Nama Mahasiswa',
        'score': 'Nilai',
        'status': 'Status'
    }
    
    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True


class SystemLogModelView(SecureModelView):
    """Admin view for SystemLog model."""
    
    # Column settings
    column_list = ['id', 'timestamp', 'level', 'category', 'user', 'message']
    column_searchable_list = ['message', 'category']
    column_filters = ['level', 'category', 'timestamp']
    column_sortable_list = ['id', 'timestamp', 'level', 'category']
    column_default_sort = ('timestamp', True)  # Sort by newest first
    
    # Display labels in Indonesian
    column_labels = {
        'id': 'ID',
        'timestamp': 'Waktu',
        'level': 'Level',
        'category': 'Kategori',
        'user': 'Pengguna',
        'message': 'Pesan'
    }
    
    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True


def setup_admin(app, admin):
    """Setup Flask-Admin with custom views."""
    # Set admin index view
    admin.index_view = SecureAdminIndexView()
    admin.init_app(app)
    
    # Add model views
    admin.add_view(UserModelView(User, db.session, name='Pengguna', category='Manajemen'))
    admin.add_view(JobModelView(Job, db.session, name='Pekerjaan', category='Data'))
    admin.add_view(JobResultModelView(JobResult, db.session, name='Hasil Penilaian', category='Data'))
    admin.add_view(SystemLogModelView(SystemLog, db.session, name='Log Sistem', category='Sistem'))
