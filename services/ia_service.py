"""Serviço simples de IA para geração de texto de relatório.

Este módulo fornece uma função `gerar_texto_relatorio` que em um cenário
real chamaria um provedor de IA externo (como OpenAI, etc.).
Aqui implementamos uma versão simplificada que apenas monta um texto
baseado nos dados fornecidos.
"""
from __future__ import annotations

from typing import Dict, Any, List


def gerar_texto_relatorio(dados: Dict[str, Any]) -> str:
    """Gera um texto de relatório a partir dos dados do evento.

    Parameters
    ----------
    dados: dict
        Dicionário contendo informações do evento e itens opcionais
        (atividades, ministrantes, etc.).

    Returns
    -------
    str
        Texto básico para o relatório. Em produção, esta função deveria
        fazer uma chamada a um serviço de IA para gerar o texto.
    """
    evento = dados.get("evento")
    partes: List[str] = []

    if evento:
        partes.append(f"Relatório do evento {evento.nome}.")

    atividades = dados.get("atividades")
    if atividades is not None:
        partes.append(f"O evento contou com {len(atividades)} atividade(s).")

    ministrantes = dados.get("ministrantes")
    if ministrantes:
        nomes = ", ".join(m.nome for m in ministrantes)
        partes.append(f"Ministrantes envolvidos: {nomes}.")

    datas = dados.get("datas")
    if datas:
        partes.append("Datas e horários:")
        for d in datas:
            partes.append(
                f"- {d['oficina']}: {d['data'].strftime('%d/%m/%Y')} "
                f"de {d['inicio']} às {d['fim']}"
            )

    sorteios = dados.get("sorteios")
    if sorteios:
        partes.append(f"Foram realizados {len(sorteios)} sorteio(s).")
        vencedores = []
        for s in sorteios:
            if s.ganhadores:
                vencedores.extend(g.nome for g in s.ganhadores)
            elif s.ganhador:
                vencedores.append(s.ganhador.nome)
        if vencedores:
            partes.append("Vencedores: " + ", ".join(vencedores) + ".")

    num_inscritos = dados.get("num_inscritos")
    if num_inscritos is not None:
        partes.append(f"Número de inscritos: {num_inscritos}.")

    lista_nominal = dados.get("lista_nominal")
    if lista_nominal:
        partes.append("Lista de inscritos:")
        for nome in lista_nominal:
            partes.append(f"- {nome}")

    checkins = dados.get("checkins")
    if checkins:
        partes.append(f"Check-ins realizados: {len(checkins)}.")

    return "\n".join(partes)
