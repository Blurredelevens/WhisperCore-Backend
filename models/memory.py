import logging
from datetime import datetime, timezone

from cryptography.fernet import Fernet

from extensions import db
from models.memory_image import MemoryImage


class Memory(db.Model):
    """Memory model for storing user memories and journal entries."""

    __tablename__ = "memories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    chat_id = db.Column(db.String(255), nullable=True, index=True)
    encrypted_content = db.Column(db.LargeBinary, nullable=False, default=b"")
    model_response = db.Column(db.LargeBinary, nullable=False, default=b"")
    tags = db.Column(db.String(200))
    is_bookmarked = db.Column(db.Boolean, default=None)
    memory_weight = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    mood_emoji = db.Column(db.String(50))

    # Relationships
    images = db.relationship("MemoryImage", back_populates="memory", cascade="all, delete-orphan")

    def to_dict(self, key):
        """Convert memory object to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "content": self._decrypt(self.encrypted_content, key),
            "model_response": self._decrypt(self.model_response, key),
            "tags": self.tags.split(",") if self.tags else [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_bookmarked": self.is_bookmarked,
            "memory_weight": self.memory_weight,
            "mood_emoji": self.mood_emoji,
            "images": [img.to_dict() for img in self.images],
            "has_images": len(self.images) > 0,
        }

    def set_content(self, content, key):
        cipher = Fernet(key)
        self.encrypted_content = cipher.encrypt(content.encode())

    def _decrypt(self, encrypted_data, key):
        """Shared decryption method for both content and model_response."""
        cipher = Fernet(key)
        try:
            return cipher.decrypt(encrypted_data).decode()
        except Exception as e:
            logging.getLogger(__name__).error(f"Decryption failed: {e}")
            return None

    def set_model_response(self, model_response, key):
        cipher = Fernet(key)
        self.model_response = cipher.encrypt(model_response.encode())

    def add_image(self, image_url, image_path=None):
        """Add an image to this memory."""

        memory_image = MemoryImage(memory_id=self.id, user_id=self.user_id, image_path=image_path)
        db.session.add(memory_image)
        return memory_image

    def get_images(self):
        """Get all images for this memory."""
        return self.images

    def has_images(self):
        """Check if memory has any images."""
        return len(self.images) > 0
