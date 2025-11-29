from flask_wtf import FlaskForm
from wtforms import SelectField, DecimalField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, ValidationError

class PromotionForm(FlaskForm):
    # Segment akan diisi secara dinamis di route
    segment_id = SelectField('Segmen Pelanggan', coerce=int, validators=[DataRequired()])
    
    promotion_type = SelectField('Jenis Promosi', choices=[
        ('percentage_discount', 'Diskon Persentase (%)'),
        ('fixed_discount', 'Diskon Tetap (Rp)')
    ], validators=[DataRequired()])
    
    # Gunakan DecimalField untuk uang/presisi angka
    promotion_value = DecimalField('Nilai Promosi', validators=[
        DataRequired(), 
        NumberRange(min=0, message='Nilai promosi tidak boleh negatif')
    ])
    
    description = TextAreaField('Deskripsi Promosi')
    submit = SubmitField('Simpan Promosi')

    # Validasi Custom: Cek logika bisnis
    def validate_promotion_value(self, field):
        if self.promotion_type.data == 'percentage_discount':
            if field.data > 100:
                raise ValidationError('Diskon persentase tidak boleh lebih dari 100%.')