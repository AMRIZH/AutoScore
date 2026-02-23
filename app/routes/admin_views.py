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
from app.models import User, Job, JobResult, SystemLog, LLMConfig


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

        # LLM status
        try:
            from app.services.llm_service import LLMService
            llm_svc = LLMService(current_app.config)
            system_info['llm_status'] = llm_svc.get_status()
        except Exception:
            system_info['llm_status'] = {'provider': 'N/A', 'model': 'N/A'}
        
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


class LLMSettingsView(BaseView):
    """Admin view for LLM provider configuration."""

    @expose('/', methods=['GET', 'POST'])
    def index(self) -> Union[Response, str]:
        import json as json_module
        from flask import current_app, jsonify

        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Anda tidak memiliki akses ke halaman admin.', 'danger')
            return redirect(url_for('auth.login'))

        if request.method == 'POST':
            provider = request.form.get('llm_provider', 'gemini')
            model = request.form.get('llm_model', '').strip()

            # Validate provider
            if provider not in ('gemini', 'nvidia', 'openai'):
                flash('Provider LLM tidak valid.', 'danger')
                return redirect(url_for('llm_settings.index'))

            try:
                LLMConfig.set('llm_provider', provider)
                LLMConfig.set('llm_model', model)

                if provider == 'gemini':
                    keys_text = request.form.get('gemini_api_keys', '').strip()
                    keys = [k.strip() for k in keys_text.splitlines() if k.strip()]
                    LLMConfig.set('gemini_api_keys', json_module.dumps(keys))
                elif provider == 'nvidia':
                    LLMConfig.set('nvidia_api_key', request.form.get('nvidia_api_key', '').strip())
                    LLMConfig.set('nvidia_base_url', request.form.get('nvidia_base_url', '').strip() or 'https://integrate.api.nvidia.com/v1')
                elif provider == 'openai':
                    LLMConfig.set('openai_api_key', request.form.get('openai_api_key', '').strip())
                    LLMConfig.set('openai_base_url', request.form.get('openai_base_url', '').strip() or 'https://api.openai.com/v1')

                SystemLog.log(
                    'INFO', 'LLM_SETTINGS',
                    f'LLM settings updated: provider={provider}, model={model}',
                    user_id=current_user.id,
                )
                flash('Pengaturan LLM berhasil disimpan!', 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.exception('Failed to save LLM settings: %s', e)
                flash('Gagal menyimpan pengaturan. Silakan coba lagi atau hubungi admin.', 'danger')

            return redirect(url_for('llm_settings.index'))

        # GET — load current config
        cfg = LLMConfig.get_all()
        gemini_keys = []
        gemini_keys_json = cfg.get('gemini_api_keys')
        if gemini_keys_json:
            try:
                gemini_keys = json_module.loads(gemini_keys_json)
            except (json_module.JSONDecodeError, TypeError):
                gemini_keys = []

        # Fall back to env keys if DB is empty
        if not gemini_keys:
            gemini_keys = list(current_app.config.get('GEMINI_API_KEYS', []))

        def _cfg_val(db_val, env_key, default=''):
            """Return DB value if not None, else fall back to env config."""
            if db_val is not None:
                return db_val
            return current_app.config.get(env_key, default)

        llm_config = {
            'provider': _cfg_val(cfg.get('llm_provider'), 'LLM_PROVIDER', 'gemini'),
            'model': _cfg_val(cfg.get('llm_model'), 'LLM_MODEL', 'gemini-2.5-flash'),
            'gemini_api_keys': '\n'.join(gemini_keys),
            'nvidia_api_key': _cfg_val(cfg.get('nvidia_api_key'), 'NVIDIA_API_KEY', ''),
            'nvidia_base_url': _cfg_val(cfg.get('nvidia_base_url'), 'NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1'),
            'openai_api_key': _cfg_val(cfg.get('openai_api_key'), 'OPENAI_API_KEY', ''),
            'openai_base_url': _cfg_val(cfg.get('openai_base_url'), 'OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        }

        return self.render('admin/llm_settings.html', llm_config=llm_config)

    @expose('/fetch-models', methods=['POST'])
    def fetch_models(self) -> Response:
        """AJAX endpoint to fetch available models from a provider."""
        from flask import jsonify, current_app
        from urllib.parse import urlparse

        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        provider = request.form.get('provider', '')
        api_key = request.form.get('api_key', '').strip()
        base_url = request.form.get('base_url', '').strip()

        if not api_key:
            return jsonify({'error': 'API key diperlukan'}), 400

        # Validate base_url against allowed provider hostnames
        ALLOWED_HOSTS = {
            'integrate.api.nvidia.com',
            'api.openai.com',
            'generativelanguage.googleapis.com',
        }
        if base_url:
            try:
                parsed = urlparse(base_url)
                if parsed.hostname not in ALLOWED_HOSTS:
                    return jsonify({'error': 'Base URL tidak diizinkan'}), 400
            except Exception:
                return jsonify({'error': 'Base URL tidak valid'}), 400

        try:
            from app.services.llm_service import LLMService
            models = LLMService.fetch_available_models(provider, api_key, base_url)
            return jsonify({'models': models})
        except Exception as e:
            current_app.logger.exception('Failed to fetch models: %s', e)
            return jsonify({'error': 'Gagal mengambil daftar model dari provider'}), 500

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
    admin.add_view(LLMSettingsView(name='Pengaturan LLM', endpoint='llm_settings', category='Sistem'))
    
    return admin
