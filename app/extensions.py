"""
Flask extensions initialization.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_admin import Admin
from apscheduler.schedulers.background import BackgroundScheduler

# Database
db = SQLAlchemy()

# Login manager
login_manager = LoginManager()

# CSRF protection
csrf = CSRFProtect()

# Admin panel - will be fully configured in setup_admin()
admin = None

# Scheduler for cleanup tasks
scheduler = BackgroundScheduler(
    job_defaults={
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 60
    },
    timezone='Asia/Jakarta'  # WIB
)
