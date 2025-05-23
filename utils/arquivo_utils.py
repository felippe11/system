def arquivo_permitido(nome_arquivo):
    extensoes_permitidas = {"csv", "xlsx", "xls"}
    return '.' in nome_arquivo and nome_arquivo.rsplit('.', 1)[1].lower() in extensoes_permitidas
