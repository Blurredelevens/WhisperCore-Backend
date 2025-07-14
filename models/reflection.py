from datetime import datetime, timezone

from extensions import db


class Reflection(db.Model):
    """Reflection model for AI-generated weekly and monthly reflections."""

    __tablename__ = "reflections"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    reflection_type = db.Column(db.String(20), nullable=False)
    period_start = db.Column(db.DateTime, nullable=False)
    period_end = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Convert reflection object to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "content": self.content,
            "reflection_type": self.reflection_type,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "created_at": self.created_at.isoformat(),
        }
