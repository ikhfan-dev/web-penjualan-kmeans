from app import db
from datetime import datetime

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # CATATAN: 
    # Relasi 'transactions' sudah otomatis ada karena backref di model Transaction
    # Relasi 'segment_memberships' sudah otomatis ada karena backref di model CustomerSegmentMembership
    
    def __repr__(self):
        return f'<Customer {self.name}>'