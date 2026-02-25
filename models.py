from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

db = SQLAlchemy()


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)

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

    created_at = db.Column(db.DateTime, default=datetime.utcnow() + timedelta(hours=5, minutes=30))

    def __repr__(self):
        return f"<Lead {self.name}>"