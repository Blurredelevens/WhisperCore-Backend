from datetime import datetime, timezone
from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

class User(db.Model):
    """User model for authentication and profile management."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    
    # Profile fields
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    bio = db.Column(db.Text)
    
    # Passphrase for additional security
    passphrase_hash = db.Column(db.String(255))
    
    # Account settings
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    # Security
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)
    
    # Relationships
    memories = db.relationship('Memory', backref='user', lazy=True, cascade='all, delete-orphan')
    reflections = db.relationship('Reflection', backref='user', lazy=True, cascade='all, delete-orphan')
    
    # Encryption
    encryption_key = db.Column(db.String(128), nullable=False, default=lambda: Fernet.generate_key().decode())
    
    # Admin
    is_admin = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    def set_passphrase(self, passphrase):
        """Hash and set the user's passphrase."""
        self.passphrase_hash = generate_password_hash(passphrase)
    
    def check_passphrase(self, passphrase):
        """Check if the provided passphrase matches the stored hash."""
        if not self.passphrase_hash:
            return False
        return check_password_hash(self.passphrase_hash, passphrase)
    
    def is_account_locked(self):
        """Check if the account is currently locked."""
        if self.locked_until and self.locked_until > datetime.now(timezone.utc):
            return True
        return False
    
    def reset_failed_attempts(self):
        """Reset failed login attempts and unlock account."""
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def increment_failed_attempts(self):
        """Increment failed login attempts and lock account if necessary."""
        self.failed_login_attempts += 1
        
        # Lock account for 1 hour after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.now(timezone.utc).replace(hour=datetime.now(timezone.utc).hour + 1)
    
    def update_last_login(self):
        """Update the last login timestamp."""
        self.last_login = datetime.now(timezone.utc)
    
    @property
    def full_name(self):
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.email.split('@')[0]
    
    def to_dict(self, include_sensitive=False):
        """Convert user object to dictionary."""
        data = {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'bio': self.bio,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'has_passphrase': bool(self.passphrase_hash),
            'image_path': self.image_path,
            'is_admin': self.is_admin
        }
        
        if include_sensitive:
            data.update({
                'failed_login_attempts': self.failed_login_attempts,
                'locked_until': self.locked_until.isoformat() if self.locked_until else None,
                'is_locked': self.is_account_locked()
            })
        
        return data 