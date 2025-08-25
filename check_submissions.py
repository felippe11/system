#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import db, Submission, WorkMetadata, Usuario
from config import Config

# Criar app Flask
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    # Verificar submissions
    submissions = db.session.query(Submission, WorkMetadata).outerjoin(
        WorkMetadata,
        (Submission.title == WorkMetadata.titulo) & 
        (Submission.evento_id == WorkMetadata.evento_id)
    ).all()
    
    print(f"Total submissions found: {len(submissions)}")
    print("\nFirst 5 submissions:")
    for i, (submission, metadata) in enumerate(submissions[:5]):
        print(f"Submission {i+1}:")
        print(f"  - Title: {submission.title if submission else 'None'}")
        print(f"  - Evento ID: {submission.evento_id if submission else 'None'}")
        print(f"  - Metadata: {metadata.titulo if metadata else 'None'}")
        print()
    
    # Verificar apenas submissions
    all_submissions = Submission.query.all()
    print(f"\nTotal Submission records: {len(all_submissions)}")
    
    # Verificar apenas metadata
    all_metadata = WorkMetadata.query.all()
    print(f"Total WorkMetadata records: {len(all_metadata)}")
    
    # Verificar usuários
    users = Usuario.query.all()
    print(f"Total users: {len(users)}")
    for user in users[:3]:
        print(f"  - User: {user.nome} ({user.tipo})")