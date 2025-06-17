from datetime import datetime
from app import db
from cryptography.fernet import Fernet

class Memory(db.Model):
    """Memory model for storing user memories and journal entries."""
    __tablename__ = 'memories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    encrypted_content = db.Column(db.LargeBinary, nullable=False, default=lambda: Fernet.generate_key().decode())
    mood = db.Column(db.String(50))
    tags = db.Column(db.String(200))
    image_path = db.Column(db.String(255))
    is_bookmarked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self, key):
        """Convert memory object to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.get_content(key),
            'mood': self.mood,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'image_path': self.image_path,
            'is_bookmarked': self.is_bookmarked
        }

    def set_content(self, content, key):
        cipher = Fernet(key)
        self.encrypted_content = cipher.encrypt(content.encode())

    def get_content(self, key):
        cipher = Fernet(key)
        return cipher.decrypt(self.encrypted_content).decode() 