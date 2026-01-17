from app import db

class AppSetting(db.Model):
    __tablename__ = 'app_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    app_name = db.Column(db.String(100), default="Aplikasi Penjualan")
    primary_color = db.Column(db.String(7), default="#0d6efd") # Default Bootstrap Blue
    
    def __repr__(self):
        return f'<AppSetting {self.app_name}>'