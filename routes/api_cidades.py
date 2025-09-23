"""Endpoints para busca de cidades brasileiras."""

from flask import Blueprint, jsonify
import requests

api_cidades = Blueprint('api_cidades', __name__)


@api_cidades.route('/get_cidades/<estado_sigla>')
def get_cidades(estado_sigla):
    """Retorna cidades do estado via API do IBGE.

    Utilizado pelos formulários que carregam cidades dinamicamente.
    """
    url = (
        "https://servicodados.ibge.gov.br/api/v1/localidades/"
        f"estados/{estado_sigla}/municipios"
    )
    response = requests.get(url)
    if response.status_code == 200:
        cidades = response.json()
        return jsonify([cidade['nome'] for cidade in cidades])
    return jsonify([])
