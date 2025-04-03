from app import app, db
from models import (
    Usuario, Oficina, OficinaDia, Inscricao, Checkin,
    Feedback, Ministrante, Cliente, ConfiguracaoCliente,
    Evento, LinkCadastro, Formulario, CampoFormulario,
    RespostaFormulario, RespostaCampo, MaterialOficina,
    RelatorioOficina, EventoInscricaoTipo, InscricaoTipo,
    RegraInscricaoEvento
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
    
    # Para prevenir erros de integridade, usar session.no_autoflush
    # em seções críticas do código
    db.session.autoflush = False

    # Create Admin - verificando CPF e email para evitar erro de duplicidade
    admin_by_email = Usuario.query.filter_by(email="admin@email.com").first()
    admin_by_cpf = Usuario.query.filter_by(cpf="00000000000").first()
    
    if admin_by_email:
        admin = admin_by_email
        print("Admin user already exists with email admin@email.com")
    elif admin_by_cpf:
        admin = admin_by_cpf
        print(f"Admin user already exists with CPF 00000000000")
    else:
        admin = Usuario(
            nome="Admin User",
            cpf="00000000000",
            email="admin@email.com",
            senha=generate_password_hash("admin123"),
            formacao="System Administrator",
            tipo="admin"
        )
        db.session.add(admin)
        print("Created new admin user")
        db.session.commit()

    # Clients
    clients = []
    client_data = [
        {"nome": "Educational Corp", "email": "educational@example.com", "habilita_pagamento": True},
        {"nome": "Training Solutions", "email": "training@example.com", "habilita_pagamento": False},
        {"nome": "Learn Forward", "email": "learn@example.com", "habilita_pagamento": True},
        {"nome": "Academia de Ciências", "email": "acad.ciencias@example.com", "habilita_pagamento": True},
        {"nome": "Instituto de Educação", "email": "instituto@example.com", "habilita_pagamento": True},
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

    # Events - Criar eventos maiores e mais diversos
    events = []
    event_data = [
        {"nome": "Conferência Nacional de Educação", "inscricao_gratuita": False, "descricao": "Grande evento anual com mais de 5000 participantes", "dias": 5},
        {"nome": "Semana de Tecnologia Educacional", "inscricao_gratuita": True, "descricao": "Exposição de novas tecnologias para educação", "dias": 7},
        {"nome": "Congresso de Professores", "inscricao_gratuita": False, "descricao": "Evento para formação continuada de professores", "dias": 3},
        {"nome": "Festival de Ciências", "inscricao_gratuita": True, "descricao": "Apresentação de projetos científicos e oficinas", "dias": 4},
        {"nome": "Simpósio de Metodologias Ativas", "inscricao_gratuita": False, "descricao": "Debate sobre novas metodologias de ensino", "dias": 2},
    ]
    
    for client in clients:
        for data in event_data:
            event = Evento(
                cliente_id=client.id,
                nome=f"{data['nome']} - {client.nome}",
                descricao=f"{data['descricao']}. Organizado por {client.nome}.",
                programacao="Programação completa disponível no site.",
                localizacao="Centro de Convenções",
                link_mapa="https://maps.google.com",
                inscricao_gratuita=data["inscricao_gratuita"],
                data_inicio=datetime.now() + timedelta(days=5),
                data_fim=datetime.now() + timedelta(days=5 + data["dias"])
            )
            db.session.add(event)
            events.append(event)

    db.session.commit()
    
    # Criar tipos de inscrição para eventos não gratuitos
    print("Criando tipos de inscrição para eventos...")
    for event in events:
        if not event.inscricao_gratuita:
            # Criar 3 tipos de inscrição para cada evento não gratuito
            tipos = [
                {"nome": "Estudante", "preco": 50.0},
                {"nome": "Professor", "preco": 80.0},
                {"nome": "Profissional", "preco": 120.0}
            ]
            
            for tipo in tipos:
                inscricao_tipo = EventoInscricaoTipo(
                    evento_id=event.id,
                    nome=tipo["nome"],
                    preco=tipo["preco"]
                )
                db.session.add(inscricao_tipo)
                db.session.flush()  # Para obter o ID
                
                # Criar regra de inscrição para este tipo
                regra = RegraInscricaoEvento(
                    evento_id=event.id,
                    tipo_inscricao_id=inscricao_tipo.id,
                    limite_oficinas=random.choice([0, 3, 5, 10])
                )
                db.session.add(regra)
                
    db.session.commit()

    # Ministrantes - Criar mais ministrantes
    ministrantes = []
    formacoes = ["Doutorado", "Mestrado", "Especialização", "MBA", "Graduação"]
    areas = ["Educação", "Tecnologia", "Ciências", "Matemática", "Linguagens", "Artes", "Metodologias Ativas", "Gestão Educacional"]
    
    # Primeiro, buscar ministrantes existentes para evitar duplicidades
    existing_emails = set()
    existing_cpfs = set()
    for m in Ministrante.query.all():
        existing_emails.add(m.email)
        existing_cpfs.add(m.cpf)
        ministrantes.append(m)
    
    # Determinar quantos ministrantes ainda precisamos criar
    num_to_create = 30 - len(ministrantes)
    print(f"Já existem {len(ministrantes)} ministrantes. Criando mais {num_to_create}...")
    
    for i in range(num_to_create):
        formacao_escolhida = random.choice(formacoes)
        area_escolhida = random.sample(areas, k=random.randint(1, 3))
        
        # Gerar um email único garantido
        email = None
        while email is None or email in existing_emails:
            unique_id = random_string(8).lower()
            email = f"min_{unique_id}@email.com"
        
        existing_emails.add(email)
        
        # Gerar um CPF único
        cpf = None
        while cpf is None or cpf in existing_cpfs:
            cpf = random_cpf()
        
        existing_cpfs.add(cpf)
        
        m = Ministrante(
            nome=f"Ministrante Novo {i+1}",
            formacao=formacao_escolhida,
            categorias_formacao=",".join(random.sample(formacoes, k=random.randint(1, 3))),
            areas_atuacao=",".join(area_escolhida),
            cpf=cpf,
            pix=f"pix_{unique_id}@email.com",
            cidade="Maceió",
            estado="AL",
            email=email,
            senha=generate_password_hash("min123"),
            cliente_id=random.choice(clients).id
        )
        db.session.add(m)
        ministrantes.append(m)

    db.session.commit()

    # Oficinas - Criar mais oficinas e com mais diversidade
    oficinas = []
    tipos_oficina = ["Oficina", "Curso", "Palestra", "Mesa Redonda", "Workshop", "Conferência", "Seminário", "outros"]
    tipos_inscricao = ["com_inscricao_com_limite", "com_inscricao_sem_limite", "sem_inscricao"]
    titulos_base = [
        "Metodologias Ativas", "Inteligência Artificial na Educação", 
        "Gamificação", "Tecnologias Educacionais", "Educação Inclusiva",
        "Avaliação Formativa", "Gestão de Sala de Aula", "Educação STEM",
        "Alfabetização", "Pensamento Computacional", "Criatividade",
        "Educação Socioemocional", "Formação de Professores"
    ]
    
    # Criar 100 oficinas com grande diversidade
    for i in range(100):
        client = random.choice(clients)
        event = random.choice([e for e in events if e.cliente_id == client.id])
        
        # Criar títulos mais interessantes
        titulo_base = random.choice(titulos_base)
        nivel = random.choice(["Básico", "Intermediário", "Avançado", "Masterclass"])
        title = f"{titulo_base}: {nivel} - Turma {i+1}"
        
        tipo_oficina = random.choice(tipos_oficina)
        
        # Garantir uma boa mistura de oficinas que precisam ou não de inscrição
        if i < 30:  # 30% sem inscrição
            tipo_inscricao = "sem_inscricao"
        elif i < 70:  # 40% com inscrição limitada
            tipo_inscricao = "com_inscricao_com_limite"
        else:  # 30% com inscrição sem limite
            tipo_inscricao = "com_inscricao_sem_limite"
        
        # Variar significativamente o número de vagas
        if tipo_inscricao == "com_inscricao_com_limite":
            vagas = random.choice([15, 20, 30, 50, 100, 150, 200, 250, 500])
        else:
            vagas = 0 if tipo_inscricao == "sem_inscricao" else 9999
        
        oficina = Oficina(
            titulo=title,
            descricao=f"Descrição detalhada da {title}. Esta atividade oferece uma experiência imersiva em {titulo_base}.",
            ministrante_id=random.choice(ministrantes).id,
            vagas=vagas,
            carga_horaria=str(random.choice([2, 4, 6, 8, 16, 20])),
            estado="AL",
            cidade="Maceió",
            cliente_id=client.id,
            evento_id=event.id,
            tipo_inscricao=tipo_inscricao,
            tipo_oficina=tipo_oficina,
            tipo_oficina_outro="Encontro Temático" if tipo_oficina == "outros" else None,
            opcoes_checkin="op1,op2,op3,op4,correct",
            palavra_correta="correct"
        )
        # Definir inscrição gratuita como atributo após criação do objeto
        # já que não está no __init__ da classe Oficina
        oficina.inscricao_gratuita = random.choice([True, False])
        db.session.add(oficina)
        db.session.flush()

        # Adicionar múltiplos dias para oficinas maiores
        num_dias = 1
        if oficina.carga_horaria in ["8", "16", "20"]:
            num_dias = int(int(oficina.carga_horaria) / 4)  # Dividir em dias de 4 horas
        
        for j in range(num_dias):
            data = random_future_date()
            hi, hf = random_time_range()
            dia = OficinaDia(oficina_id=oficina.id, data=data, horario_inicio=hi, horario_fim=hf)
            db.session.add(dia)

        oficinas.append(oficina)

    db.session.commit()

    # Para oficinas que não são gratuitas, criar tipos de inscrição
    print("Criando tipos de inscrição para oficinas...")
    for oficina in oficinas:
        if not oficina.inscricao_gratuita:
            tipos = [
                {"nome": "Estudante", "preco": 20.0},
                {"nome": "Professor", "preco": 35.0},
                {"nome": "Profissional", "preco": 50.0}
            ]
            
            for tipo in tipos:
                tipo_inscricao = InscricaoTipo(
                    oficina_id=oficina.id,
                    nome=tipo["nome"],
                    preco=tipo["preco"]
                )
                db.session.add(tipo_inscricao)
    
    db.session.commit()

    # Participantes - Criar muito mais participantes
    participantes = []
    cidades = ["Maceió", "Rio Largo", "Marechal Deodoro", "Arapiraca", "Palmeira dos Índios", "Penedo"]
    formacoes_part = ["Estudante", "Professor", "Coordenador", "Diretor", "Pesquisador"]
    
    # Primeiro, buscar participantes existentes para evitar duplicidades
    existing_emails = set()
    existing_cpfs = set()
    for p in Usuario.query.filter_by(tipo="participante").all():
        existing_emails.add(p.email)
        existing_cpfs.add(p.cpf)
        participantes.append(p)
    
    # Determinar quantos participantes ainda precisamos criar
    num_to_create = 2000 - len(participantes)
    print(f"Já existem {len(participantes)} participantes. Criando mais {num_to_create}...")
    
    for i in range(num_to_create):
        # Gerar um email único garantido
        email = None
        while email is None or email in existing_emails:
            unique_id = random_string(8).lower()
            email = f"part_{unique_id}@mail.com"
        
        existing_emails.add(email)
        
        # Gerar um CPF único garantido
        cpf = None
        while cpf is None or cpf in existing_cpfs:
            cpf = random_cpf()
        
        existing_cpfs.add(cpf)
        
        # Escolher um cliente aleatório
        cliente = random.choice(clients)
        
        # Escolher um evento deste cliente
        evento = random.choice([e for e in events if e.cliente_id == cliente.id])
        
        # Escolher um tipo de inscrição aleatório se o evento não for gratuito
        tipo_inscricao_id = None
        if not evento.inscricao_gratuita:
            tipos_inscricao = EventoInscricaoTipo.query.filter_by(evento_id=evento.id).all()
            if tipos_inscricao:
                tipo_inscricao_id = random.choice(tipos_inscricao).id
        
        p = Usuario(
            nome=f"Participante Novo {i+1}",
            cpf=cpf,
            email=email,
            senha=generate_password_hash("part123"),
            formacao=random.choice(formacoes_part),
            tipo="participante",
            cliente_id=cliente.id,
            evento_id=evento.id,
            tipo_inscricao_id=tipo_inscricao_id,
            estados="AL",
            cidades=random.choice(cidades)
        )
        db.session.add(p)
        participantes.append(p)
        
        # Commit a cada 100 participantes para evitar problemas de memória
        if i > 0 and i % 100 == 0:
            db.session.commit()
            print(f"   - {i} participantes criados...")

    db.session.commit()

    # Inscrições e Checkins - Criar muitas inscrições para simular eventos grandes
    print("Criando inscrições...")
    
    # Armazenar pares (usuario_id, oficina_id) para evitar duplicidades
    existing_inscricoes = set()
    for ins in Inscricao.query.all():
        existing_inscricoes.add((ins.usuario_id, ins.oficina_id))
    
    print(f"Já existem {len(existing_inscricoes)} inscrições no sistema.")
    
    inscricoes_count = 0
    checkins_count = 0
    
    # Definir quantas inscrições criar para cada oficina com base em suas vagas
    for oficina in oficinas:
        # Pular oficinas sem inscrição
        if oficina.tipo_inscricao == "sem_inscricao":
            continue
            
        # Obter tipos de inscrição para esta oficina (se não for gratuita)
        tipos_inscricao = []
        if not oficina.inscricao_gratuita:
            tipos_inscricao = InscricaoTipo.query.filter_by(oficina_id=oficina.id).all()
        
        # Definir o número de inscrições a serem criadas
        if oficina.tipo_inscricao == "com_inscricao_com_limite":
            # Preencher entre 70% e 110% das vagas (algumas podem ficar em lista de espera)
            num_inscricoes = int(oficina.vagas * random.uniform(0.7, 1.1))
        else:  # com_inscricao_sem_limite
            # Criar entre 50 e 300 inscrições para oficinas sem limite
            num_inscricoes = random.randint(50, 300)
        
        # Garante que não ultrapasse o número de participantes disponíveis
        num_inscricoes = min(num_inscricoes, len(participantes))
        
        # Escolher aleatoriamente participantes para esta oficina
        selected_participants = random.sample(participantes, num_inscricoes)
        
        # Criar as inscrições
        for part in selected_participants:
            # Verificar se esta inscrição já existe
            if (part.id, oficina.id) not in existing_inscricoes:
                existing_inscricoes.add((part.id, oficina.id))
                
                try:
                    ins = Inscricao(usuario_id=part.id, oficina_id=oficina.id, cliente_id=oficina.cliente_id)
                    
                    # Atribuir um tipo de inscrição se a oficina não for gratuita
                    if not oficina.inscricao_gratuita and tipos_inscricao:
                        ins.tipo_inscricao_id = random.choice(tipos_inscricao).id
                    
                    # Certificar que o usuário tenha tipo de inscrição no evento
                    if oficina.evento_id:
                        # Definir o evento no usuário
                        if not part.evento_id:
                            part.evento_id = oficina.evento_id
                            db.session.add(part)
                        
                        # Se o evento não for gratuito, garantir que o usuário tenha um tipo de inscrição
                        evento = Evento.query.get(oficina.evento_id)
                        if not evento.inscricao_gratuita and not part.tipo_inscricao_id:
                            tipos_evento = EventoInscricaoTipo.query.filter_by(evento_id=oficina.evento_id).all()
                            if tipos_evento:
                                part.tipo_inscricao_id = random.choice(tipos_evento).id
                                db.session.add(part)
                    
                    db.session.add(ins)
                    inscricoes_count += 1
                    
                    # Para cerca de 60% dos inscritos, criar um checkin também
                    if random.random() < 0.6:
                        ck = Checkin(
                            usuario_id=part.id,
                            oficina_id=oficina.id,
                            data_hora=datetime.now() - timedelta(days=random.randint(1, 3)),
                            palavra_chave="correct"
                        )
                        db.session.add(ck)
                        checkins_count += 1
                    
                    # Commit a cada 200 inscrições para evitar sobrecarga
                    if inscricoes_count % 200 == 0:
                        try:
                            db.session.commit()
                            print(f"   - {inscricoes_count} novas inscrições criadas...")
                        except IntegrityError as e:
                            print(f"Erro de integridade ao criar inscrições: {e}")
                            db.session.rollback()
                
                except Exception as e:
                    print(f"Erro ao criar inscrição para usuario_id={part.id}, oficina_id={oficina.id}: {e}")
                    db.session.rollback()

    db.session.commit()
    print(f"Total de inscrições criadas: {Inscricao.query.count()}")
    print(f"Total de checkins criados: {Checkin.query.count()}")
    
    # Adicionar alguns feedbacks
    print("Adicionando feedbacks...")
    
    # Armazenar pares (usuario_id, oficina_id) para evitar duplicidades em feedbacks
    existing_feedbacks = set()
    for fb in Feedback.query.all():
        if fb.usuario_id and fb.oficina_id:
            existing_feedbacks.add((fb.usuario_id, fb.oficina_id))
    
    print(f"Já existem {len(existing_feedbacks)} feedbacks no sistema.")
    
    feedback_count = 0
    feedback_limit = 500
    
    # Obter todas as inscrições que têm checkin
    checkins = Checkin.query.all()
    print(f"Existem {len(checkins)} checkins para potenciais feedbacks.")
    
    if checkins:
        # Embaralhar os checkins para selecionar aleatoriamente
        random.shuffle(checkins)
        
        for checkin in checkins[:feedback_limit]:
            # Verificar se já existe feedback para esta combinação usuário/oficina
            if (checkin.usuario_id, checkin.oficina_id) not in existing_feedbacks:
                try:
                    # Adicionar feedback
                    fb = Feedback(
                        usuario_id=checkin.usuario_id,
                        oficina_id=checkin.oficina_id,
                        rating=random.randint(1, 5),
                        comentario=f"Comentário sobre a oficina {checkin.oficina_id}. {'Muito bom!' if random.random() > 0.3 else 'Pode melhorar.'}"
                    )
                    db.session.add(fb)
                    feedback_count += 1
                    existing_feedbacks.add((checkin.usuario_id, checkin.oficina_id))
                    
                    # Commit a cada 50 feedbacks
                    if feedback_count % 50 == 0:
                        try:
                            db.session.commit()
                            print(f"   - {feedback_count} novos feedbacks criados...")
                        except Exception as e:
                            print(f"Erro ao commitar feedbacks: {e}")
                            db.session.rollback()
                
                except Exception as e:
                    print(f"Erro ao criar feedback: {e}")
                    db.session.rollback()
                
                # Parar quando atingir o limite
                if feedback_count >= feedback_limit:
                    break
    
    db.session.commit()
    print(f"Total de feedbacks criados: {Feedback.query.count()}")
    
    print("\u2705 População de banco concluída com sucesso!")
    print(f"""
    Resumo da população:
    - Clientes: {Cliente.query.count()}
    - Eventos: {Evento.query.count()}
    - Tipos de Inscrição em Eventos: {EventoInscricaoTipo.query.count()}
    - Regras de Inscrição: {RegraInscricaoEvento.query.count()}
    - Ministrantes: {Ministrante.query.count()}
    - Oficinas: {Oficina.query.count()}
    - Tipos de Inscrição em Oficinas: {InscricaoTipo.query.count()}
    - Participantes: {Usuario.query.filter_by(tipo="participante").count()}
    - Inscrições: {Inscricao.query.count()}
    - Checkins: {Checkin.query.count()}
    - Feedbacks: {Feedback.query.count()}
    """)

if __name__ == "__main__":
    with app.app_context():
        populate_database()