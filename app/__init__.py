"""
AutoScoring Flask Application
Lab FKI Universitas Muhammadiyah Surakarta

Aplikasi untuk menilai laporan praktikum mahasiswa secara otomatis menggunakan LLM.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from werkzeug.security import generate_password_hash

from app.config import Config
from app.extensions import db, login_manager, csrf, admin, scheduler


def create_app(config_class=Config):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Silakan login terlebih dahulu untuk mengakses halaman ini.'
    login_manager.login_message_category = 'warning'
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    
    # Setup Flask-Admin
    from app.routes.admin_views import setup_admin
    setup_admin(app, admin)
    
    # Create database tables and seed data
    with app.app_context():
        db.create_all()
        seed_default_users()
        log_gpu_status(app)
    
    # Setup cleanup scheduler
    if app.config['ENABLE_CLEANUP']:
        setup_scheduler(app)
    
    # Cleanup on startup
    if app.config['CLEANUP_ON_STARTUP']:
        with app.app_context():
            from app.services.cleanup_service import cleanup_temp_files
            cleanup_temp_files(app)
    
    app.logger.info('Aplikasi AutoScoring berhasil dijalankan')
    
    return app


def setup_logging(app):
    """Configure application logging."""
    # Create logs directory if not exists
    log_dir = os.path.join(app.root_path, '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'autoscoring.log')
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    file_handler.setLevel(logging.INFO)
    
    # Add handler to app logger
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    
    # Also log to console in debug mode
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)


def seed_default_users():
    """Create default admin and aslab users if they don't exist."""
    from app.models import User
    
    # Check if users already exist
    if User.query.filter_by(username='admin').first() is None:
        admin_user = User(
            username='admin',
            password_hash=generate_password_hash('informatika'),
            role='admin'
        )
        db.session.add(admin_user)
        db.session.commit()
    
    if User.query.filter_by(username='aslab').first() is None:
        aslab_user = User(
            username='aslab',
            password_hash=generate_password_hash('informatika1'),
            role='aslab'
        )
        db.session.add(aslab_user)
        db.session.commit()


def log_gpu_status(app):
    """Log GPU/CPU mode status."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            app.logger.info(f'Mode GPU aktif: {gpu_name} ({gpu_memory:.1f} GB)')
            app.config['GPU_AVAILABLE'] = True
            app.config['GPU_NAME'] = gpu_name
        else:
            app.logger.info('Mode CPU aktif (GPU tidak tersedia)')
            app.config['GPU_AVAILABLE'] = False
            app.config['GPU_NAME'] = None
    except ImportError:
        app.logger.info('Mode CPU aktif (PyTorch tidak terinstall)')
        app.config['GPU_AVAILABLE'] = False
        app.config['GPU_NAME'] = None


def setup_scheduler(app):
    """Setup APScheduler for cleanup tasks."""
    from app.services.cleanup_service import scheduled_cleanup
    
    # Only start scheduler in main process (not reloader)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        scheduler.add_job(
            func=scheduled_cleanup,
            trigger='cron',
            hour=2,  # 02:00 WIB
            minute=0,
            id='daily_cleanup',
            replace_existing=True,
            args=[app]
        )
        scheduler.start()
        app.logger.info('Scheduler cleanup harian aktif (02:00 WIB)')
