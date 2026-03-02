from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import string

db = SQLAlchemy()

def generate_id(length=8):
    chars = string.ascii_lowercase + string.digits

    while True:
        new_id = ''.join(secrets.choice(chars) for _ in range(length))

        existing = User.query.filter_by(name=new_id).first()

        if not existing:
            return new_id

def ist():
    return datetime.utcnow() + timedelta(hours=5, minutes=30)

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    phone2 = db.Column(db.String(20))
    email = db.Column(db.String(150), nullable=False)

    designation = db.Column(db.String(150))
    company = db.Column(db.String(150))
    customer_type = db.Column(db.String(150))
    website = db.Column(db.String(150))
    address = db.Column(db.Text)
    remarks = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=ist)

    is_deleted = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Lead {self.name}>"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, default=generate_id)
    password = db.Column(db.String(200), nullable=False)

    def set_password(self, raw_password):
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password, raw_password)