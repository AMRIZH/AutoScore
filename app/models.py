"""
Database models for AutoScoring application.
"""

from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """User model for authentication."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='aslab')  # 'admin' or 'aslab'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationship to jobs
    jobs = db.relationship('Job', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'
    
    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


class Job(db.Model):
    """Scoring job model."""
    
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Job settings
    score_min = db.Column(db.Integer, default=40)
    score_max = db.Column(db.Integer, default=100)
    enable_evaluation = db.Column(db.Boolean, default=True)
    
    # Files
    answer_key_path = db.Column(db.String(500), nullable=True)
    question_doc_paths = db.Column(db.Text, nullable=True)  # JSON array of paths
    total_files = db.Column(db.Integer, default=0)
    processed_files = db.Column(db.Integer, default=0)
    
    # Additional notes for scoring
    additional_notes = db.Column(db.Text, nullable=True)
    
    # Status: 'pending', 'processing', 'completed', 'failed'
    status = db.Column(db.String(20), default='pending')
    status_message = db.Column(db.String(500), nullable=True)
    
    # Results
    result_csv_path = db.Column(db.String(500), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship to results
    results = db.relationship('JobResult', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Job {self.id} - {self.status}>'


class JobResult(db.Model):
    """Individual student result within a job."""
    
    __tablename__ = 'job_results'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    
    # Student info
    filename = db.Column(db.String(255), nullable=False)
    nim = db.Column(db.String(50), nullable=True)
    student_name = db.Column(db.String(255), nullable=True)
    
    # Scoring
    score = db.Column(db.Integer, nullable=True)
    evaluation = db.Column(db.Text, nullable=True)
    
    # Status: 'pending', 'processing', 'completed', 'error'
    status = db.Column(db.String(20), default='pending')
    error_message = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<JobResult {self.id} - {self.nim}>'


class SystemLog(db.Model):
    """System log for auditing."""
    
    __tablename__ = 'system_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    level = db.Column(db.String(20), nullable=False)  # INFO, WARNING, ERROR
    category = db.Column(db.String(50), nullable=False)  # login, upload, llm, cleanup, etc.
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text, nullable=True)  # JSON string for extra details
    
    # Relationship to user
    user = db.relationship('User', backref='logs')
    
    def __repr__(self):
        return f'<SystemLog {self.id} - {self.category}>'
    
    @classmethod
    def log(cls, level, category, message, user_id=None, details=None):
        """Create a new log entry."""
        log_entry = cls(
            level=level,
            category=category,
            message=message,
            user_id=user_id,
            details=details
        )
        db.session.add(log_entry)
        db.session.commit()
        return log_entry
