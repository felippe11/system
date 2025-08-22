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
        except Exception:
            return jsonify({"message": "Erro ao ler o arquivo"}), 400

        title_column = request.form.get("title_column")
        if not title_column or title_column not in df.columns:
            title_column = df.columns[0] if not df.columns.empty else None

        raw_records = df.to_dict(orient="records")
        records = []
        for row_dict in raw_records:
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
            records.append(attributes)

        temp_id = uuid.uuid4().hex
        temp_path = os.path.join(
            tempfile.gettempdir(), f"import_trabalhos_{temp_id}.json"
        )
        with open(temp_path, "w", encoding="utf-8") as tmp:
            json.dump(records, tmp)

        preview = records[:5]
        return jsonify(
            {
                "columns": df.columns.tolist(),
                "preview": preview,
                "temp_id": temp_id,
            }
        )

    temp_id = request.form.get("temp_id")
    if not temp_id:
        return jsonify({"error": "missing temp_id"}), 400

    temp_path = os.path.join(
        tempfile.gettempdir(), f"import_trabalhos_{temp_id}.json"
    )
    try:
        with open(temp_path, "r", encoding="utf-8") as tmp:
            rows = json.load(tmp)
    except FileNotFoundError:
        return jsonify({"error": "invalid temp_id"}), 400

    columns = request.form.getlist("columns")
    title_column = request.form.get("title_column")

    imported = 0
    for idx, row in enumerate(rows, start=1):
        raw_title = row.get(title_column) if title_column else None
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

        selected = {col: row.get(col) for col in columns} if columns else row
        wm = WorkMetadata(
            data=selected,
            titulo=selected.get("titulo"),
            categoria=selected.get("categoria"),
            rede_ensino=selected.get("rede_ensino"),
            etapa_ensino=selected.get("etapa_ensino"),
            pdf_url=selected.get("pdf_url"),
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
        return jsonify({"error": msg}), 400

    try:
        os.remove(temp_path)
    except OSError:
        pass

    return jsonify({"status": "ok", "imported": imported})
