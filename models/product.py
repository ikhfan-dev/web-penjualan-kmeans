from app import db

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))
    unit = db.Column(db.String(20), default='pcs')
    
    # Relasi dengan item transaksi
    transaction_items = db.relationship('TransactionItem', backref='product', lazy='dynamic')
    
    def __repr__(self):
        return f'<Product {self.name}>'