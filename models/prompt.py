from extensions import db
from datetime import datetime, timezone

class Prompt(db.Model):
    __tablename__ = 'prompts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'is_active': self.is_active,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
    def from_dict(self, data):
        for field in ['text', 'is_active']:
            if field in data:
                setattr(self, field, data[field])
        return self
        
        
    def save(self):
        db.session.add(self)
        db.session.commit()


    def update(self, data):
        for field in ['text', 'is_active']:
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