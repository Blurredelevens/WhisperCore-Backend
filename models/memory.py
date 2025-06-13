from datetime import datetime
from app import db

class Memory(db.Model):
    """Memory model for storing user memories and journal entries."""
    __tablename__ = 'memories'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(50))  # For mood tagging
    tags = db.Column(db.String(200))  # Comma-separated tags
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert memory object to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'content': self.content,
            'mood': self.mood,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        } 