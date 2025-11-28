from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, IntegerField, SelectField, SubmitField, ValidationError
from wtforms.validators import DataRequired, NumberRange
from models.product import Product

class ProductForm(FlaskForm):
    sku = StringField('SKU', validators=[DataRequired()])
    name = StringField('Nama Produk', validators=[DataRequired()])
    description = TextAreaField('Deskripsi')
    price = FloatField('Harga', validators=[DataRequired(), NumberRange(min=0)])
    stock = IntegerField('Stok', validators=[DataRequired(), NumberRange(min=0)])
    category = SelectField('Kategori', choices=[
        ('makanan', 'Makanan'),
        ('minuman', 'Minuman'),
        ('elektronik', 'Elektronik'),
        ('pakaian', 'Pakaian'),
        ('lainnya', 'Lainnya')
    ], default='lainnya')
    unit = StringField('Satuan', validators=[DataRequired()],default='PCS')
    submit = SubmitField('Simpan')
    
    def validate_sku(self, sku):
        product = Product.query.filter_by(sku=sku.data).first()
        if product and not hasattr(self, 'product') or (hasattr(self, 'product') and self.product.id != product.id):
            raise ValidationError('SKU sudah digunakan.')