import sys
import os
from sqlalchemy import text

# Add the parent directory to sys.path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db

def add_categoria_column():
    app = create_app()
    with app.app_context():
        # Check if column exists
        with db.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(atividade_multipla_data)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'categoria' not in columns:
                print("Adding 'categoria' column to 'atividade_multipla_data' table...")
                try:
                    conn.execute(text("ALTER TABLE atividade_multipla_data ADD COLUMN categoria VARCHAR(100)"))
                    conn.commit()
                    print("Column added successfully.")
                except Exception as e:
                    print("Error adding column: {}".format(e))
            else:
                print("Column 'categoria' already exists.")

if __name__ == "__main__":
    add_categoria_column()
