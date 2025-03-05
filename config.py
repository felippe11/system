import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.urandom(24)  # Gera uma chave aleatória
    #SQLALCHEMY_DATABASE_URI = 'postgresql://iafap:tOsydfgBrVx1o57X7oqznlABbwlFek84@dpg-cug5itl6l47c739tgung-a/iafap_database'
    
    SQLALCHEMY_DATABASE_URI = 'postgresql://iafap:iafap@localhost:5432/iafap_database'
  
    #'postgresql://iafap:tOsydfgBrVx1o57X7oqznlABbwlFek84@dpg-cug5itl6l47c739tgung-a/iafap_database' render
    #postgresql://iafap:iafap@localhost:5432/iafap_database  local
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configuração para envio de e-mails via Gmail
    MAIL_SERVER = 'smtp.gmail.com'  # Servidor SMTP do Gmail
    MAIL_PORT = 587  # Porta para envio de e-mails
    MAIL_USE_TLS = True  # Usa TLS para segurança
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')  # Seu e-mail
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')  # Sua senha
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_USERNAME')  # O e-mail que enviará as mensagens
    
    

