"""
Flask-Admin views for AutoScoring application.
"""

from typing import Union
from flask import redirect, url_for, request, flash, Response
from flask_admin import AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from wtforms import PasswordField, IntegerField, BooleanField
from wtforms.validators import NumberRange, DataRequired
from werkzeug.security import generate_password_hash
from flask_wtf import FlaskForm

from app.extensions import db
from app.models import User, Job, JobResult, SystemLog


class SecureAdminIndexView(AdminIndexView):
    """Secure admin index view - only accessible by admin users."""
    
    @expose('/')
    def index(self) -> Union[Response, str]:
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Anda tidak memiliki akses ke halaman admin.', 'danger')
            return redirect(url_for('auth.login'))
        
        from flask import current_app
        system_info = {
            'gpu_available': current_app.config.get('GPU_AVAILABLE', False),
            'gpu_name': current_app.config.get('GPU_NAME', 'N/A'),
            'max_pdf_count': current_app.config.get('MAX_PDF_COUNT', 50),
            'enable_cleanup': current_app.config.get('ENABLE_CLEANUP', True),
            'enable_ocr': current_app.config.get('ENABLE_OCR', True),
            'max_workers': current_app.config.get('MAX_WORKERS', 4)
        }
        
        stats = {
            'total_users': User.query.count(),
            'total_jobs': Job.query.count(),
            'completed_jobs': Job.query.filter_by(status='completed').count(),
            'failed_jobs': Job.query.filter_by(status='failed').count()
        }
        
        return self.render('admin/index.html', system_info=system_info, stats=stats)
    
    def is_accessible(self) -> bool:
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name: str, **kwargs) -> Response:
        flash('Anda tidak memiliki akses ke halaman admin.', 'danger')
        return redirect(url_for('auth.login', next=request.url))


class SecureModelView(ModelView):
    """Base secure model view - only accessible by admin users."""
    
    def is_accessible(self) -> bool:
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name: str, **kwargs) -> Response:
        flash('Anda tidak memiliki akses ke halaman admin.', 'danger')
        return redirect(url_for('auth.login', next=request.url))


class UserModelView(SecureModelView):
    """Admin view for User model with password management."""
    
    column_list = ['id', 'username', 'role', 'created_at', 'last_login']
    column_searchable_list = ['username']
    column_filters = ['role', 'created_at']
    column_sortable_list = ['id', 'username', 'role', 'created_at', 'last_login']
    
    form_columns = ['username', 'role', 'password']
    form_extra_fields = {
        'password': PasswordField('Password Baru')
    }
    
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
    
    def on_model_change(self, form, model: User, is_created: bool) -> None:
        """Handle password hashing when creating/updating user."""
        if form.password.data:
            model.password_hash = generate_password_hash(form.password.data)


class JobModelView(SecureModelView):
    """Admin view for Job model."""
    
    column_list = ['id', 'user', 'status', 'total_files', 'processed_files', 'created_at', 'completed_at']
    column_searchable_list = ['status']
    column_filters = ['status', 'created_at', 'user_id']
    column_sortable_list = ['id', 'status', 'total_files', 'created_at', 'completed_at']
    
    column_labels = {
        'id': 'ID',
        'user': 'Pengguna',
        'status': 'Status',
        'total_files': 'Total File',
        'processed_files': 'File Diproses',
        'created_at': 'Dibuat',
        'completed_at': 'Selesai'
    }
    
    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True


class JobResultModelView(SecureModelView):
    """Admin view for JobResult model."""
    
    column_list = ['id', 'job_id', 'filename', 'nim', 'student_name', 'score', 'status']
    column_searchable_list = ['nim', 'student_name', 'filename']
    column_filters = ['status', 'score', 'job_id']
    column_sortable_list = ['id', 'job_id', 'score', 'status']
    
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
    
    column_list = ['id', 'timestamp', 'level', 'category', 'user', 'message']
    column_searchable_list = ['message', 'category']
    column_filters = ['level', 'category', 'timestamp']
    column_sortable_list = ['id', 'timestamp', 'level', 'category']
    column_default_sort = ('timestamp', True)
    
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


class SettingsForm(FlaskForm):
    """Form for runtime settings."""
    max_file_size_mb = IntegerField(
        'Max File Size (MB)',
        validators=[DataRequired(), NumberRange(min=1, max=100)]
    )
    max_pdf_count = IntegerField(
        'Max PDF Count',
        validators=[DataRequired(), NumberRange(min=1, max=500)]
    )
    enable_ocr = BooleanField('Enable OCR')
    enable_cleanup = BooleanField('Enable Cleanup')


class SettingsView(BaseView):
    """Admin view for runtime settings modification."""
    
    @expose('/', methods=['GET', 'POST'])
    def index(self) -> Union[Response, str]:
        from flask import current_app
        
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Anda tidak memiliki akses ke halaman admin.', 'danger')
            return redirect(url_for('auth.login'))
        
        form = SettingsForm()
        
        if request.method == 'GET':
            form.max_file_size_mb.data = current_app.config.get('MAX_FILE_SIZE_MB', 10)
            form.max_pdf_count.data = current_app.config.get('MAX_PDF_COUNT', 50)
            form.enable_ocr.data = current_app.config.get('ENABLE_OCR', True)
            form.enable_cleanup.data = current_app.config.get('ENABLE_CLEANUP', True)
        
        if form.validate_on_submit():
            current_app.config['MAX_FILE_SIZE_MB'] = form.max_file_size_mb.data
            current_app.config['MAX_PDF_COUNT'] = form.max_pdf_count.data
            current_app.config['ENABLE_OCR'] = form.enable_ocr.data
            current_app.config['ENABLE_CLEANUP'] = form.enable_cleanup.data
            
            # Log the settings change
            try:
                log = SystemLog(
                    level='INFO',
                    category='SETTINGS',
                    user_id=current_user.id,
                    message=f'Settings updated: MAX_FILE_SIZE_MB={form.max_file_size_mb.data}, '
                            f'MAX_PDF_COUNT={form.max_pdf_count.data}, '
                            f'ENABLE_OCR={form.enable_ocr.data}, '
                            f'ENABLE_CLEANUP={form.enable_cleanup.data}'
                )
                db.session.add(log)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.exception('Failed to write audit log for settings change: %s', e)
                flash('Pengaturan diperbarui, tetapi gagal mencatat log audit.', 'warning')
            
            flash('Pengaturan berhasil diperbarui!', 'success')
            return redirect(url_for('settings.index'))
        
        return self.render('admin/settings.html', form=form)
    
    def is_accessible(self) -> bool:
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name: str, **kwargs) -> Response:
        flash('Anda tidak memiliki akses ke halaman admin.', 'danger')
        return redirect(url_for('auth.login', next=request.url))


def setup_admin(app):
    """Setup Flask-Admin with custom views."""
    from flask_admin import Admin
    from flask_admin.theme import Bootstrap4Theme
    
    admin = Admin(
        app,
        name='AutoScoring Admin',
        theme=Bootstrap4Theme(),
        index_view=SecureAdminIndexView(name='Home', url='/admin')
    )
    
    admin.add_view(UserModelView(User, db.session, name='Pengguna', category='Manajemen'))
    admin.add_view(JobModelView(Job, db.session, name='Pekerjaan', category='Data'))
    admin.add_view(JobResultModelView(JobResult, db.session, name='Hasil Penilaian', category='Data'))
    admin.add_view(SystemLogModelView(SystemLog, db.session, name='Log Sistem', category='Sistem'))
    admin.add_view(SettingsView(name='Pengaturan', endpoint='settings', category='Sistem'))
    
    return admin
