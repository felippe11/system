# utils.py

def arquivo_permitido(filename):
    extensoes_permitidas = {'xls', 'xlsx', 'csv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensoes_permitidas
