from models import Checkin, Oficina, Evento, CertificadoTemplate
from models.user import Cliente
from models.review import ConfiguracaoCertificadoEvento
from sqlalchemy import func


def verificar_criterios_certificado(usuario_id, evento_id):
    """Verifica se o participante atende aos critérios de certificado."""
    config = ConfiguracaoCertificadoEvento.query.filter_by(evento_id=evento_id).first()
    if not config:
        return True, []

    pendencias = []

    total_checkins = Checkin.query.filter_by(usuario_id=usuario_id, evento_id=evento_id).count()
    if config.checkins_minimos and total_checkins < config.checkins_minimos:
        pendencias.append(f"Mínimo de {config.checkins_minimos} check-ins (atual {total_checkins})")

    for oficina_id in config.get_oficinas_obrigatorias_list():
        tem = Checkin.query.filter_by(usuario_id=usuario_id, oficina_id=oficina_id).first()
        if not tem:
            ofi = Oficina.query.get(oficina_id)
            pendencias.append(f"Participar da oficina '{ofi.titulo if ofi else oficina_id}'")

    if config.percentual_minimo:
        total_oficinas = Oficina.query.filter_by(evento_id=evento_id).count()
        if total_oficinas:
            presentes = (
                Checkin.query.join(Oficina, Checkin.oficina_id == Oficina.id)
                .filter(Checkin.usuario_id == usuario_id, Oficina.evento_id == evento_id)
                .with_entities(Checkin.oficina_id).distinct().count()
            )
            percentual = (presentes / total_oficinas) * 100
            if percentual < config.percentual_minimo:
                pendencias.append(f"Participação mínima de {config.percentual_minimo}% (atual {int(percentual)}%)")

    return len(pendencias) == 0, pendencias
