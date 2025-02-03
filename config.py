import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.urandom(24)  # Gera uma chave aleatória
    SQLALCHEMY_DATABASE_URI = 'postgresql://iafap:iafap@localhost:5432/iafap_database' 
    SQLALCHEMY_TRACK_MODIFICATIONS = False

