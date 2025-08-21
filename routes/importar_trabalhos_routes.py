"""Endpoints for importing work metadata from spreadsheets."""

import json
import uuid
from flask import Blueprint, request, jsonify
import pandas as pd
from extensions import db
from werkzeug.security import generate_password_hash
from models import WorkMetadata, Submission

importar_trabalhos_routes = Blueprint(
    "importar_trabalhos_routes", __name__
)


@importar_trabalhos_routes.route("/importar_trabalhos", methods=["POST"])
def importar_trabalhos():
    """Import metadata from an uploaded spreadsheet.

    The endpoint supports two phases:
    1. Upload an Excel file via ``arquivo`` to preview available columns.
    2. Submit selected ``columns`` and ``data`` (JSON list) to persist them.
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

        imported = 0
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            raw_title = row_dict.get(title_column) if title_column else None
            if raw_title is None or (isinstance(raw_title, float) and pd.isna(raw_title)):
                title = f"Trabalho {imported + 1}"
            else:
                title = str(raw_title)
            submission = Submission(
                title=title,
                code_hash=generate_password_hash(uuid.uuid4().hex),
                evento_id=evento_id,
                attributes=row_dict,
            )
            db.session.add(submission)
            imported += 1

        if imported:
            db.session.commit()

        return jsonify(
            {
                "columns": df.columns.tolist(),
                "data": df.to_dict(orient="records"),
                "imported": imported,
            }
        )

    columns = request.form.getlist("columns")
    data_json = request.form.get("data")

    if not data_json:
        return jsonify({"error": "missing data"}), 400

    rows = json.loads(data_json)
    if not columns and rows:
        columns = list(rows[0].keys())

    for row in rows:
        selected = {col: row.get(col) for col in columns}
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
    db.session.commit()
    return jsonify({"status": "ok", "message": "Importação concluída"})
