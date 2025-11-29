from app import db

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False) # Diperlebar jadi 50 char
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # PENTING: Gunakan Numeric untuk uang
    price = db.Column(db.Numeric(12, 2), nullable=False) 
    
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))
    unit = db.Column(db.String(20), default='pcs')
    
    # Relasi 'transaction_items' akan otomatis ada via backref di TransactionItem
    
    def __repr__(self):
        return f'<Product {self.name}>'