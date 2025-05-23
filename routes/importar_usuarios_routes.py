from flask import Blueprint, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_required
import pandas as pd
import os

from extensions import db
from models import Usuario
from flask import current_app
from utils.arquivo_utils import arquivo_permitido





importar_usuarios_routes = Blueprint('importar_usuarios_routes', __name__)


@importar_usuarios_routes.route("/importar_usuarios", methods=["POST"])
def importar_usuarios():
    if "arquivo" not in request.files:
        flash("Nenhum arquivo enviado!", "danger")
        return redirect(url_for("routes.dashboard"))
    arquivo = request.files["arquivo"]
    if arquivo.filename == "":
        flash("Nenhum arquivo selecionado.", "danger")
        return redirect(url_for("routes.dashboard"))
    if arquivo and arquivo_permitido(arquivo.filename):
        filename = secure_filename(arquivo.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        arquivo.save(filepath)
        try:
            print("📌 [DEBUG] Lendo o arquivo Excel...")
            df = pd.read_excel(filepath, dtype={"cpf": str})
            print(f"📌 [DEBUG] Colunas encontradas: {df.columns.tolist()}")
            colunas_obrigatorias = ["nome", "cpf", "email", "senha", "formacao", "tipo"]
            if not all(col in df.columns for col in colunas_obrigatorias):
                flash("Erro: O arquivo deve conter as colunas: " + ", ".join(colunas_obrigatorias), "danger")
                return redirect(url_for("routes.dashboard"))
            total_importados = 0
            for _, row in df.iterrows():
                cpf_str = str(row["cpf"]).strip()
                usuario_existente = Usuario.query.filter_by(email=row["email"]).first()
                if usuario_existente:
                    print(f"⚠️ [DEBUG] Usuário com e-mail {row['email']} já existe. Pulando...")
                    continue
                usuario_existente = Usuario.query.filter_by(cpf=cpf_str).first()
                if usuario_existente:
                    print(f"⚠️ [DEBUG] Usuário com CPF {cpf_str} já existe. Pulando...")
                    continue
                senha_hash = generate_password_hash(str(row["senha"]))
                novo_usuario = Usuario(
                    nome=row["nome"],
                    cpf=cpf_str,
                    email=row["email"],
                    senha=senha_hash,
                    formacao=row["formacao"],
                    tipo=row["tipo"]
                )
                db.session.add(novo_usuario)
                total_importados += 1
                print(f"✅ [DEBUG] Usuário '{row['nome']}' cadastrado com sucesso!")
            db.session.commit()
            flash(f"{total_importados} usuários importados com sucesso!", "success")
        except Exception as e:
            db.session.rollback()
            print(f"❌ [ERRO] Erro ao importar usuários: {str(e)}")
            flash(f"Erro ao processar o arquivo: {str(e)}", "danger")
        os.remove(filepath)
    else:
        flash("Formato de arquivo inválido. Envie um arquivo Excel (.xlsx)", "danger")
    return redirect(url_for("routes.dashboard"))


