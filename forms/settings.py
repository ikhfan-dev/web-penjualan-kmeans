from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length

class AppSettingForm(FlaskForm):
    app_name = StringField('Nama Aplikasi', validators=[DataRequired(), Length(max=100)])
    primary_color = StringField('Warna Tema Utama (Hex)', validators=[DataRequired(), Length(max=7)])
    submit = SubmitField('Simpan Perubahan')