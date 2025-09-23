import requests

try:
    response = requests.get('http://localhost:5000/revisor/selecionar_categoria_barema/341')
    print(f'Status Code: {response.status_code}')
    print(f'Headers: {dict(response.headers)}')
    print(f'Content: {response.text[:500]}...' if len(response.text) > 500 else response.text)
except Exception as e:
    print(f'Error: {e}')