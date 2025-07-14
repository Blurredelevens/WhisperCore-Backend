from datetime import datetime, timezone
from extensions import db
from cryptography.fernet import Fernet
import logging

class Memory(db.Model):
    """Memory model for storing user memories and journal entries."""
    __tablename__ = 'memories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    chat_id = db.Column(db.String(255), nullable=True, index=True)
    encrypted_content = db.Column(db.LargeBinary, nullable=False, default=b'')
    model_response = db.Column(db.LargeBinary, nullable=False, default=b'')
    mood = db.Column(db.String(50))
    tags = db.Column(db.String(200))
    image_path = db.Column(db.String(255))
    is_bookmarked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    mood_emoji = db.Column(db.String(50))
    mood_value = db.Column(db.Integer)
    
    def to_dict(self, key):
        """Convert memory object to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'content': self.get_content(key),
            'model_response': self.get_model_response(key),
            'mood': self.mood,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'image_path': self.image_path,
            'is_bookmarked': self.is_bookmarked,
            'mood_emoji': self.mood_emoji,
            'mood_value': self.mood_value
        }

    def to_dict_with_keys(self, encryption_key, model_key):
        """Convert memory object to dictionary using separate keys for content and model_response."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'chat_id': self.chat_id,
            'content': self.get_content(encryption_key),
            'model_response': self.get_model_response(model_key),
            'mood': self.mood,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'image_path': self.image_path,
            'is_bookmarked': self.is_bookmarked,
            'mood_emoji': self.mood_emoji,
            'mood_value': self.mood_value
        }

    def set_content(self, content, key):
        cipher = Fernet(key)
        self.encrypted_content = cipher.encrypt(content.encode())

    def get_content(self, key):
        cipher = Fernet(key)
        try:
            return cipher.decrypt(self.encrypted_content).decode()
        except Exception as e:
            logging.getLogger(__name__).error(f"Decryption failed for content: {e}")
            return None
    
    def set_model_response(self, model_response, key):
        cipher = Fernet(key)
        self.model_response = cipher.encrypt(model_response.encode())

    def get_model_response(self, key):
        cipher = Fernet(key)
        try:
            return cipher.decrypt(self.model_response).decode()
        except Exception as e:
            logging.getLogger(__name__).error(f"Decryption failed for model_response: {e}")
            return None