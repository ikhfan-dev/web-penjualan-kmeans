from app import db
from datetime import datetime

class CustomerSegment(db.Model):
    __tablename__ = 'customer_segments'
    
    id = db.Column(db.Integer, primary_key=True)
    segment_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#007bff')  # Hex color code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CustomerSegment {self.segment_name}>'
    
class Promotion(db.Model):
    __tablename__ = 'promotions'
    
    id = db.Column(db.Integer, primary_key=True)
    segment_id = db.Column(db.Integer, db.ForeignKey('customer_segments.id', ondelete='CASCADE'), nullable=False)
    segment_id = db.Column(db.Integer, db.ForeignKey('customer_segments.id'), unique=True, nullable=False)
    promotion_type = db.Column(db.String(50), nullable=False) # 'percentage_discount', 'fixed_discount', 'buy_x_get_y'
    promotion_value = db.Column(db.Float, nullable=False) # 10 untuk 10%, 50000 untuk Rp 50000
    description = db.Column(db.String(255))
    
    # Buat relasi one-to-one dengan CustomerSegment
    segment = db.relationship('CustomerSegment', backref=db.backref('promotion', uselist=False))
    
    def __repr__(self):
        return f'<Promotion for {self.segment.segment_name}>'

class CustomerSegmentMembership(db.Model):
    __tablename__ = 'customer_segment_membership'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    segment_id = db.Column(db.Integer, db.ForeignKey('customer_segments.id', ondelete='CASCADE'), nullable=False)
    segment_id = db.Column(db.Integer, db.ForeignKey('customer_segments.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Definisikan relasi dari sini. Backref akan otomatis membuat atribut di model lain.
    customer = db.relationship('Customer', backref=db.backref('segment_memberships', lazy='dynamic', cascade='all, delete-orphan'))
    segment = db.relationship('CustomerSegment', backref=db.backref('memberships', lazy='dynamic', cascade='all, delete-orphan'))
    
    __table_args__ = (db.UniqueConstraint('customer_id', 'segment_id'),)
    
    def __repr__(self):
        return f'<CustomerSegmentMembership {self.customer_id}-{self.segment_id}>'