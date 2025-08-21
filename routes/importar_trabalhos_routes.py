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
        df = pd.read_excel(file)

        for _, row in df.iterrows():
            title = row.get("title") or row.get("titulo")
            if not title:
                continue
            submission = Submission(
                title=title,
                code_hash=generate_password_hash(uuid.uuid4().hex),
                evento_id=evento_id,
            )
            db.session.add(submission)
        if not df.empty:
            db.session.commit()

        return jsonify({
            "columns": df.columns.tolist(),
            "data": df.to_dict(orient="records"),
        })

    columns = request.form.getlist("columns")
    data_json = request.form.get("data")

    if not data_json:
        return jsonify({"error": "missing data"}), 400

    rows = json.loads(data_json)
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
