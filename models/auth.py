"""
User authentication models for RTSP Recorder application
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
# Import the existing SQLAlchemy instance from notifications
from models.notification import db

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    relationship = db.Column(db.String(50), nullable=True, default='Guardian')
    active = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    first_login = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationship with login logs
    login_logs = db.relationship('LoginLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_id(self):
        """Return user id as string for Flask-Login"""
        return str(self.id)
    
    @property
    def is_active(self):
        """Return whether user is active (required by Flask-Login)"""
        return self.active
    
    @property
    def is_authenticated(self):
        """Return True if user is authenticated"""
        return True
    
    @property
    def is_anonymous(self):
        """Return False as user is not anonymous"""
        return False
    
    def __repr__(self):
        return f'<User {self.username}>'

class LoginLog(db.Model):
    """Login log model to track user logins"""
    __tablename__ = 'login_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # IPv6 can be up to 45 characters
    user_agent = db.Column(db.Text)
    
    def __repr__(self):
        return f'<LoginLog {self.user_id} at {self.login_time}>'

def init_db(app):
    """Initialize auth database tables and default admin user"""
    # Database is already initialized by notification_manager.init_app(app)
    # We just need to create our tables
    with app.app_context():
        # Create all tables (including User and LoginLog tables)
        db.create_all()
        
        # Create default admin user if not exists
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            admin_user = User()
            admin_user.username = 'admin'
            admin_user.email = 'admin@localhost'
            admin_user.relationship = 'Father'
            admin_user.active = True
            admin_user.is_admin = True
            admin_user.first_login = True
            admin_user.set_password('password')
            db.session.add(admin_user)
            db.session.commit()
            print("[INFO] Default admin user created (username: admin, password: password, relationship: Father)")
