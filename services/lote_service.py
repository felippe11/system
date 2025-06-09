# services/lote_service.py
from datetime import datetime
from sqlalchemy import func
from extensions import db
from models import Inscricao
from routes import routes

def lote_disponivel(lote):
    now = datetime.utcnow()
    if lote.data_inicio and lote.data_fim:
        if not (lote.data_inicio <= now <= lote.data_fim):
            return False
    if lote.qtd_maxima is not None:
        usados = db.session.query(func.count(Inscricao.id)).filter(
            Inscricao.lote_id == lote.id,
            Inscricao.status_pagamento.in_(["approved", "pending"])
        ).scalar()
        if usados >= lote.qtd_maxima:
            return False
    return True

@routes.route('/api/lote_vigente/<int:evento_id>', methods=['GET'])
def api_lote_vigente(evento_id):
    from datetime import datetime
    from extensions import db
    from flask import jsonify
    from models import LoteInscricao, Inscricao
    import logging

    logger = logging.getLogger(__name__)
    now = datetime.utcnow()

    try:
        lotes = LoteInscricao.query.filter_by(evento_id=evento_id, ativo=True).order_by(LoteInscricao.ordem).all()
        lote_vigente = None

        for lote in lotes:
            count = Inscricao.query.filter_by(
                evento_id=evento_id, 
                lote_id=lote.id
            ).filter(
                Inscricao.status_pagamento.in_(["approved", "pending"])
            ).count()

            is_valid = True

            # Verificação por datas
            if lote.data_inicio and lote.data_fim:
                if not (lote.data_inicio <= now <= lote.data_fim):
                    is_valid = False

            # Verificação por quantidade
            if lote.qtd_maxima is not None and count >= lote.qtd_maxima:
                is_valid = False

            # Verificação se tem tipo de inscrição associado
            if not lote.tipos_inscricao:
                is_valid = False

            if is_valid:
                lote_vigente = lote
                break

        if lote_vigente:
            return jsonify({
                'success': True,
                'lote_id': lote_vigente.id,
                'nome': lote_vigente.nome,
                'vagas_totais': lote_vigente.qtd_maxima,
                'vagas_usadas': count,
                'vagas_disponiveis': lote_vigente.qtd_maxima - count if lote_vigente.qtd_maxima else "ilimitado",
                'data_inicio': lote_vigente.data_inicio.isoformat() if lote_vigente.data_inicio else None,
                'data_fim': lote_vigente.data_fim.isoformat() if lote_vigente.data_fim else None
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nenhum lote válido encontrado'
            })

    except Exception as e:
        logger.error(f"Erro na API lote_vigente: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Erro ao verificar lote vigente: {str(e)}'
        })



