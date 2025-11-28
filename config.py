import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '1234567890'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://sql12809524:5lY5J1gSta@sql12.freesqldatabase.com/sql12809524'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    
    # Konfigurasi untuk K-Means
    KMEANS_N_CLUSTERS = 3  # Jumlah cluster default