"""Endpoints for importing work metadata from spreadsheets."""

import json
import os
import tempfile
import uuid
from flask import Blueprint, jsonify, request
import pandas as pd
from extensions import db
from werkzeug.security import generate_password_hash
from models import Submission, WorkMetadata
from sqlalchemy.exc import DataError

importar_trabalhos_routes = Blueprint(
    "importar_trabalhos_routes", __name__
)


@importar_trabalhos_routes.route("/importar_trabalhos", methods=["POST"])
def importar_trabalhos():
    """Import metadata from an uploaded spreadsheet.

    The endpoint supports two phases:

    1. Upload an Excel file via ``arquivo``. The spreadsheet is parsed and
       temporarily stored, returning available column names and a preview of the
       rows.
    2. Post ``temp_id`` and optionally ``columns`` to persist the stored data as
       ``Submission`` and ``WorkMetadata`` records.
    """
    evento_id = request.form.get("evento_id", type=int)
    if "arquivo" in request.files:
        file = request.files["arquivo"]
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return jsonify({"success": False, "message": f"Erro ao ler o arquivo: {str(e)}"}), 400

        records = df.to_dict(orient="records")
        rows = []
        for row_dict in records:
            attributes = {}
            for key, value in row_dict.items():
                if isinstance(value, pd.Timestamp):
                    value = value.isoformat()
                elif pd.isna(value):
                    value = None
                elif hasattr(value, "item"):
                    value = value.item()
                if not isinstance(value, (str, int, float, bool, type(None))):
                    value = str(value)
                attributes[key] = value
            rows.append(attributes)

        temp_id = uuid.uuid4().hex
        temp_path = os.path.join(
            tempfile.gettempdir(), f"import_trabalhos_{temp_id}.json"
        )
        with open(temp_path, "w", encoding="utf-8") as tmp:
            json.dump(rows, tmp)

        preview = rows[:5]


        return jsonify(
            {
                "success": True,
                "temp_id": temp_id,
                "columns": df.columns.tolist(),
                "data": preview,
                "message": "Arquivo processado com sucesso"
            }
        )

    temp_id = request.form.get("temp_id")
    if not temp_id:
        return jsonify({"success": False, "message": "ID temporário não fornecido"}), 400

    temp_path = os.path.join(
        tempfile.gettempdir(), f"import_trabalhos_{temp_id}.json"
    )
    try:
        with open(temp_path, "r", encoding="utf-8") as tmp:
            rows = json.load(tmp)
    except FileNotFoundError:
        return jsonify({"success": False, "message": "ID temporário inválido ou expirado"}), 400

    # Obter mapeamento de colunas do formulário
    titulo_col = request.form.get("titulo")
    categoria_col = request.form.get("categoria")
    rede_ensino_col = request.form.get("rede_ensino")
    etapa_ensino_col = request.form.get("etapa_ensino")
    pdf_url_col = request.form.get("pdf_url")

    imported = 0
    for idx, row in enumerate(rows, start=1):
        # Obter título usando o mapeamento
        raw_title = row.get(titulo_col) if titulo_col else None
        title = str(raw_title) if raw_title else f"Trabalho {idx}"
        
        submission = Submission(
            title=title,
            code_hash=generate_password_hash(
                uuid.uuid4().hex, method="pbkdf2:sha256"
            ),
            evento_id=evento_id,
            attributes=row,
        )
        db.session.add(submission)

        # Criar WorkMetadata usando o mapeamento de colunas
        wm = WorkMetadata(
            data=row,
            titulo=row.get(titulo_col) if titulo_col else None,
            categoria=row.get(categoria_col) if categoria_col else None,
            rede_ensino=row.get(rede_ensino_col) if rede_ensino_col else None,
            etapa_ensino=row.get(etapa_ensino_col) if etapa_ensino_col else None,
            pdf_url=row.get(pdf_url_col) if pdf_url_col else None,
            evento_id=evento_id,
        )
        db.session.add(wm)
        imported += 1

    try:
        db.session.commit()
    except DataError as err:
        db.session.rollback()
        column = getattr(
            getattr(getattr(err, "orig", None), "diag", None),
            "column_name",
            None,
        )
        msg = (
            f"Valor inválido para o campo '{column}'"
            if column
            else "Valor inválido para um dos campos"
        )
        return jsonify({"success": False, "message": msg}), 400

    try:
        os.remove(temp_path)
    except OSError:
        pass

    message = f"Importação concluída! {imported} trabalhos importados."
    
    return jsonify({"success": True, "status": "ok", "imported": imported, "message": message})
