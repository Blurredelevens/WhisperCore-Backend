from datetime import datetime, timezone

from extensions import db


class MemoryImage(db.Model):
    """MemoryImage model for storing multiple images per memory."""

    __tablename__ = "memory_images"

    id = db.Column(db.Integer, primary_key=True)
    memory_id = db.Column(db.Integer, db.ForeignKey("memories.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    memory = db.relationship("Memory", back_populates="images")
    user = db.relationship("User", backref="memory_images")

    def to_dict(self):
        """Convert memory image object to dictionary."""
        return {
            "id": self.id,
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "image_path": self.image_path,
            "created_at": self.created_at.isoformat(),
        }

    def save(self):
        """Save the memory image to database."""
        db.session.add(self)
        db.session.commit()
        return self

    def delete(self):
        """Delete the memory image from database."""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_id(cls, image_id):
        """Get memory image by ID."""
        return db.session.get(cls, image_id)

    @classmethod
    def get_by_memory_id(cls, memory_id):
        """Get all images for a specific memory."""
        return cls.query.filter_by(memory_id=memory_id).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_by_user_id(cls, user_id):
        """Get all images for a specific user."""
        return cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_memories_with_images(cls, user_id):
        """Get all memories that have images for a specific user."""
        from models.memory import Memory

        return Memory.query.join(cls).filter(cls.user_id == user_id).distinct().all()

    @classmethod
    def get_memories_without_images(cls, user_id):
        """Get all memories that don't have images for a specific user."""
        from models.memory import Memory

        return (
            Memory.query.outerjoin(cls)
            .filter(
                Memory.user_id == user_id,
                cls.id.is_(None),
            )
            .all()
        )
