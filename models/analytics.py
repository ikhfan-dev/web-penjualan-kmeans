from app import db
from datetime import datetime

class CustomerSegment(db.Model):
    __tablename__ = 'customer_segments'
    
    id = db.Column(db.Integer, primary_key=True)
    segment_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(7), default='#007bff')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Backref 'memberships' dan 'promotion' otomatis terbuat dari tabel lain
    
    def __repr__(self):
        return f'<CustomerSegment {self.segment_name}>'

class Promotion(db.Model):
    __tablename__ = 'promotions'
    
    id = db.Column(db.Integer, primary_key=True)
    # Hapus duplikasi column segment_id, sisakan satu yang benar
    segment_id = db.Column(db.Integer, db.ForeignKey('customer_segments.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    promotion_type = db.Column(db.String(50), nullable=False)
    # Gunakan Numeric agar perhitungan diskon akurat
    promotion_value = db.Column(db.Numeric(10, 2), nullable=False) 
    description = db.Column(db.String(255))
    
    segment = db.relationship('CustomerSegment', backref=db.backref('promotion', uselist=False))
    
    def __repr__(self):
        return f'<Promotion Segment {self.segment_id}>'

class CustomerSegmentMembership(db.Model):
    __tablename__ = 'customer_segment_membership'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    # Hapus duplikasi, sisakan satu
    segment_id = db.Column(db.Integer, db.ForeignKey('customer_segments.id', ondelete='CASCADE'), nullable=False)
    
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Definisi Relasi & Backref
    # backref='segment_memberships' akan otomatis menambahkan properti .segment_memberships ke model Customer
    customer = db.relationship('Customer', backref=db.backref('segment_memberships', lazy='dynamic', cascade='all, delete-orphan'))
    segment = db.relationship('CustomerSegment', backref=db.backref('memberships', lazy='dynamic', cascade='all, delete-orphan'))
    
    __table_args__ = (db.UniqueConstraint('customer_id', 'segment_id'),)
    
    def __repr__(self):
        return f'<Membership {self.customer_id}-{self.segment_id}>'