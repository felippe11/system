
from app import create_app
from extensions import db
from sqlalchemy import inspect
import sys

def check_tables():
    app = create_app()
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            feedback_tables = [
                "feedback_aberto_perguntas",
                "feedback_aberto_dias",
                "feedback_aberto_dia_perguntas",
                "feedback_aberto_envios",
                "feedback_aberto_respostas"
            ]
            
            all_exist = True
            for table in feedback_tables:
                if table in tables:
                    print(f"PASS: Table '{table}' exists.")
                else:
                    print(f"FAIL: Table '{table}' does NOT exist.")
                    all_exist = False
            
            if all_exist:
                print("SUCCESS: All feedback tables exist.")
            else:
                print("FAILURE: Some feedback tables are missing.")
                
        except Exception as e:
            print(f"Error checking tables: {e}")

if __name__ == "__main__":
    check_tables()
