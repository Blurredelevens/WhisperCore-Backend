from datetime import datetime, timezone

from extensions import db


class Prompt(db.Model):
    __tablename__ = "prompts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def from_dict(self, data):
        for field in ["text", "is_active"]:
            if field in data:
                setattr(self, field, data[field])
        return self

    def save(self):
        db.session.add(self)
        db.session.commit()

    def update(self, data):
        for field in ["text", "is_active"]:
            if field in data:
                setattr(self, field, data[field])
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_all():
        return Prompt.query.all()

    @staticmethod
    def get_by_id(id):
        return db.session.get(Prompt, id)

    @staticmethod
    def get_by_is_active(is_active):
        return Prompt.query.filter_by(is_active=is_active).all()

    @staticmethod
    def get_today_prompt(user_id):
        """Get today's prompt for a user."""
        today = datetime.now(timezone.utc).date()
        return (
            Prompt.query.filter_by(user_id=user_id, is_active=True)
            .filter(db.func.date(Prompt.created_at) == today)
            .first()
        )

    @staticmethod
    def get_today_prompts(user_id):
        """Get all today's prompts for a user."""
        today = datetime.now(timezone.utc).date()
        return (
            Prompt.query.filter_by(user_id=user_id, is_active=True)
            .filter(db.func.date(Prompt.created_at) == today)
            .order_by(Prompt.created_at.desc())
            .all()
        )

    @staticmethod
    def get_latest_prompts(user_id):
        """Get latest prompts for a user."""
        return (
            Prompt.query.filter_by(user_id=user_id, is_active=True)
            .order_by(Prompt.created_at.desc(), Prompt.id.desc())
            .limit(5)
            .all()
        )

    @staticmethod
    def create_daily_prompt(user_id, prompt_text):
        # TOOD: Change this to use llm
        """Create a new daily prompt for a user."""

        # Check if prompt already exists for this user today
        existing = Prompt.get_today_prompt(user_id)
        if existing:
            existing.text = prompt_text
            existing.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            return existing

        daily_prompt = Prompt(user_id=user_id, text=prompt_text, is_active=True)
        daily_prompt.save()
        return daily_prompt

    @staticmethod
    def create_personalized_prompt(user_id, prompt_text):
        """Create a personalized prompt for a user (allows multiple per day)."""
        personalized_prompt = Prompt(user_id=user_id, text=prompt_text, is_active=True)
        personalized_prompt.save()
        return personalized_prompt
