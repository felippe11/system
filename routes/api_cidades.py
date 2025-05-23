from flask import Blueprint
import requests
from flask import jsonify
from flask import current_app

api_cidades = Blueprint('api_cidades', __name__)

@api_cidades.route('/get_cidades/<estado_sigla>')
def get_cidades(estado_sigla):
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{estado_sigla}/municipios"
    response = requests.get(url)
    if response.status_code == 200:
        cidades = response.json()
        return jsonify([cidade['nome'] for cidade in cidades])
    return jsonify([])