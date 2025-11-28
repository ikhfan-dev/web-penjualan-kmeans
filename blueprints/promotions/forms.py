from flask_wtf import FlaskForm
from wtforms import SelectField, FloatField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from models.analytics import CustomerSegment, Promotion

class PromotionForm(FlaskForm):
    # Segment akan diisi secara dinamis di route
    segment_id = SelectField('Segmen', coerce=int, validators=[DataRequired()])
    
    promotion_type = SelectField('Jenis Promosi', choices=[
        ('percentage_discount', 'Diskon Persentase (%)'),
        ('fixed_discount', 'Diskon Tetap (Rp)')
    ], validators=[DataRequired()])
    
    promotion_value = FloatField('Nilai Promosi', validators=[
        DataRequired(), 
        NumberRange(min=0, message='Nilai promosi tidak boleh negatif')
    ])
    
    description = TextAreaField('Deskripsi Promosi')
    submit = SubmitField('Simpan Promosi')