# /home/erickdaniellv/refacajeme/config.py
import os

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///C:/Users/Erick Lopez/Desktop/WEBS/eridan123/instance/mydatabase.db')
    #SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///mydatabase.db')

    #SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:////home/erickdaniellv/eridan123/db/catalogo.db')
    #SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://erickdaniellv:Eridan123@erickdaniellv.mysql.pythonanywhere-services.com/erickdaniellv$Refacajemedb'
    #SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
        
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False


    WTF_CSRF_ENABLED = True


    MAIL_SERVER = 'smtp.hostinger.com'
    MAIL_PORT = 587  # 465 Para SSL, o cambia a 587 si es TLS
    MAIL_USE_TLS = True  # Cambia a False si estás usando SSL
    MAIL_USE_SSL = False  # Añade esto si estás usando SSL
    MAIL_USERNAME = 'eridan123@eridan123.com'
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'default-password')
    MAIL_DEFAULT_SENDER = 'eridan123@eridan123.com'