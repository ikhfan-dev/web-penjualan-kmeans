from app import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Tipe data keuangan
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(12, 2), default=0.0)
    
    payment_method = db.Column(db.String(20), default='cash')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relasi ke Parent
    # backref='transactions' membuat customer.transactions bisa diakses
    customer = db.relationship('Customer', backref=db.backref('transactions', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('transactions', lazy='dynamic'))
    
    # Relasi ke Child (Items)
    items = db.relationship('TransactionItem', backref='transaction', lazy='joined', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Transaction {self.id}>'

class TransactionItem(db.Model):
    __tablename__ = 'transaction_items'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Relasi ke Product
    product = db.relationship('Product', backref=db.backref('transaction_items', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TransactionItem {self.id}>'