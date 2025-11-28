from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp
from models.analytics import CustomerSegment

class SegmentForm(FlaskForm):
    segment_name = StringField('Nama Segmen', validators=[
        DataRequired(), 
        Length(min=3, max=50, message='Nama segmen harus antara 3 dan 50 karakter.')
    ])
    
    description = TextAreaField('Deskripsi Segmen')
    
    color = StringField('Warna Segmen (Hex)', validators=[
        DataRequired(),
        Regexp(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', message='Format warna tidak valid. Gunakan format hex seperti #FF5733.')
    ], default='#007bff')
    
    submit = SubmitField('Simpan Segmen')