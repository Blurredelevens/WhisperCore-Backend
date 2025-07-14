from datetime import datetime, timezone

from extensions import db


class Token(db.Model):
    __tablename__ = "tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(10), nullable=False)  # 'access' or 'refresh'
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_value = db.Column(db.Text, nullable=False)  # Store the actual token
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Relationship
    user = db.relationship("User", backref="tokens")

    def __repr__(self):
        return f"<Token {self.jti} - {self.token_type}>"

    @classmethod
    def create_token(cls, jti, token_type, user_id, token_value, expires_at):
        """Create and store a new token."""
        token = cls(jti=jti, token_type=token_type, user_id=user_id, token_value=token_value, expires_at=expires_at)
        db.session.add(token)
        db.session.commit()
        return token

    @classmethod
    def upsert_token(cls, jti, token_type, user_id, token_value, expires_at):
        token = cls.query.filter_by(user_id=user_id, token_type=token_type).first()
        if token:
            token.jti = jti
            token.token_value = token_value
            token.expires_at = expires_at
            token.is_active = True
        else:
            token = cls(
                jti=jti,
                token_type=token_type,
                user_id=user_id,
                token_value=token_value,
                expires_at=expires_at,
                is_active=True,
            )
            db.session.add(token)
        db.session.commit()
        return token

    @classmethod
    def is_token_active(cls, jti):
        """Check if a token is active (not revoked and not expired)."""
        token = cls.query.filter_by(jti=jti, is_active=True).first()
        if not token:
            return False
        now = datetime.now(timezone.utc)
        expires_at = (
            token.expires_at.replace(tzinfo=timezone.utc) if token.expires_at.tzinfo is None else token.expires_at
        )
        if expires_at < now:
            return False
        return True

    @classmethod
    def revoke_token(cls, jti):
        """Revoke a specific token by JTI."""
        token = cls.query.filter_by(jti=jti).first()
        if token:
            token.is_active = False
            db.session.commit()
            return True
        return False

    @classmethod
    def deactivate_user_tokens(cls, user_id, token_type=None):
        """Deactivate all tokens for a user (or specific token type)."""
        query = cls.query.filter_by(user_id=user_id, is_active=True)
        if token_type:
            query = query.filter_by(token_type=token_type)

        tokens = query.all()
        for token in tokens:
            token.is_active = False
        db.session.commit()
        return len(tokens)

    @classmethod
    def cleanup_expired_tokens(cls):
        """Remove expired tokens."""
        expired_tokens = cls.query.filter(cls.expires_at < datetime.now(timezone.utc)).all()
        for token in expired_tokens:
            db.session.delete(token)
        db.session.commit()
        return len(expired_tokens)
