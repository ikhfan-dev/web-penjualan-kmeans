from app import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    total_amount = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(20), default='cash')  # cash, card, transfer
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relasi dengan item transaksi
    items = db.relationship('TransactionItem', backref='transaction', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Transaction {self.id}>'

class TransactionItem(db.Model):
    __tablename__ = 'transaction_items'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Harga saat transaksi (bisa berbeda dari harga produk saat ini)
    
    def __repr__(self):
        return f'<TransactionItem {self.id}>'