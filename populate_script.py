from app import app, db
from models import (
    Usuario, Oficina, OficinaDia, Inscricao, Checkin,
    Feedback, Ministrante, Cliente, ConfiguracaoCliente,
    Evento, LinkCadastro, Formulario, CampoFormulario,
    RespostaFormulario, RespostaCampo, MaterialOficina,
    RelatorioOficina
)
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random
import string
import os
from sqlalchemy.exc import IntegrityError

# Function to generate random strings
def random_string(length):
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))

# Function to generate random CPF
def random_cpf():
    return ''.join(random.choice(string.digits) for _ in range(11))

# Function to generate random date in the future
def random_future_date(days_ahead_min=10, days_ahead_max=60):
    days_ahead = random.randint(days_ahead_min, days_ahead_max)
    return datetime.now().date() + timedelta(days=days_ahead)

# Function to generate start and end time
def random_time_range():
    start_hour = random.randint(8, 14)
    end_hour = start_hour + random.randint(2, 4)
    start_time = f"{start_hour:02d}:00"
    end_time = f"{end_hour:02d}:00"
    return start_time, end_time

def create_directory_if_not_exists(path):
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)

# Populate the database
def populate_database():
    print("\U0001F680 Starting database population...")

    # Create Admin
    admin = Usuario.query.filter_by(email="admin@email.com").first()
    if not admin:
        admin = Usuario(
            nome="Admin User",
            cpf="00000000000",
            email="admin@email.com",
            senha=generate_password_hash("admin123"),
            formacao="System Administrator",
            tipo="admin"
        )
        db.session.add(admin)

    # Clients
    clients = []
    client_data = [
        {"nome": "Educational Corp", "email": "educational@example.com", "habilita_pagamento": True},
        {"nome": "Training Solutions", "email": "training@example.com", "habilita_pagamento": False},
        {"nome": "Learn Forward", "email": "learn@example.com", "habilita_pagamento": True},
    ]

    for data in client_data:
        client = Cliente.query.filter_by(email=data["email"]).first()
        if not client:
            client = Cliente(
                nome=data["nome"],
                email=data["email"],
                senha=generate_password_hash("client123"),
                habilita_pagamento=data["habilita_pagamento"],
                ativo=True
            )
            db.session.add(client)
            clients.append(client)
            db.session.flush()

            config = ConfiguracaoCliente(
                cliente_id=client.id,
                permitir_checkin_global=True,
                habilitar_feedback=True,
                habilitar_certificado_individual=True
            )
            db.session.add(config)
        else:
            clients.append(client)

    db.session.commit()

    # Events
    events = []
    for client in clients:
        for name in [f"Event A - {client.nome}", f"Event B - {client.nome}"]:
            event = Evento(
                cliente_id=client.id,
                nome=name,
                descricao=f"Descrição do evento {name}.",
                programacao="Programação completa aqui.",
                localizacao="Centro de Convenções",
                link_mapa="https://maps.google.com",
                inscricao_gratuita=True,
                data_inicio=datetime.now() + timedelta(days=5),
                data_fim=datetime.now() + timedelta(days=8)
            )
            db.session.add(event)
            events.append(event)

    db.session.commit()

    # Ministrantes
    ministrantes = []
    for i in range(5):
        m = Ministrante(
            nome=f"Ministrante {i+1}",
            formacao="Doutorado",
            categorias_formacao="Doutorado,Mestrado",
            areas_atuacao="Educação",
            cpf=random_cpf(),
            pix=f"pix{i+1}@email.com",
            cidade="Maceió",
            estado="AL",
            email=f"min{i+1}@email.com",
            senha=generate_password_hash("min123"),
            cliente_id=random.choice(clients).id
        )
        db.session.add(m)
        ministrantes.append(m)

    db.session.commit()

    # Oficinas
    oficinas = []
    for i in range(10):
        client = random.choice(clients)
        event = random.choice([e for e in events if e.cliente_id == client.id])
        title = f"Oficina {i+1}"

        tipo_oficina = random.choice(["Oficina", "Curso", "outros"])
        tipo_inscricao = random.choice(["com_inscricao_com_limite", "com_inscricao_sem_limite", "sem_inscricao"])

        oficina = Oficina(
            titulo=title,
            descricao="Descrição da oficina",
            ministrante_id=random.choice(ministrantes).id,
            vagas=random.randint(10, 50),
            carga_horaria="8",
            estado="AL",
            cidade="Maceió",
            cliente_id=client.id,
            evento_id=event.id,
            tipo_inscricao=tipo_inscricao,
            tipo_oficina=tipo_oficina,
            tipo_oficina_outro="Mesa Redonda" if tipo_oficina == "outros" else None,
            opcoes_checkin="op1,op2,op3,op4,correct",
            palavra_correta="correct"
        )
        db.session.add(oficina)
        db.session.flush()

        for j in range(random.randint(1, 3)):
            data = random_future_date()
            hi, hf = random_time_range()
            dia = OficinaDia(oficina_id=oficina.id, data=data, horario_inicio=hi, horario_fim=hf)
            db.session.add(dia)

        oficinas.append(oficina)

    db.session.commit()

    # Participantes
    participantes = []
    for i in range(20):
        p = Usuario(
            nome=f"Participante {i+1}",
            cpf=random_cpf(),
            email=f"part{i+1}@mail.com",
            senha=generate_password_hash("part123"),
            formacao="Estudante",
            tipo="participante",
            cliente_id=random.choice(clients).id,
            estados="AL",
            cidades="Maceió"
        )
        db.session.add(p)
        participantes.append(p)

    db.session.commit()

    # Inscrições e Checkins
    for _ in range(50):
        part = random.choice(participantes)
        ofc = random.choice(oficinas)
        if not Inscricao.query.filter_by(usuario_id=part.id, oficina_id=ofc.id).first():
            ins = Inscricao(usuario_id=part.id, oficina_id=ofc.id, cliente_id=ofc.cliente_id)
            db.session.add(ins)
            if random.choice([True, False]):
                ck = Checkin(
                    usuario_id=part.id,
                    oficina_id=ofc.id,
                    data_hora=datetime.now() - timedelta(days=random.randint(1, 3)),
                    palavra_chave="correct"
                )
                db.session.add(ck)

    db.session.commit()
    print("\u2705 População de banco concluída com sucesso!")

if __name__ == "__main__":
    with app.app_context():
        populate_database()
