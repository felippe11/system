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
    print("🚀 Starting database population...")

    # Create Admin if not exists
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
        print("✅ Admin user created")

    # Create Clients
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
            
            # Create client configuration
            config = ConfiguracaoCliente(
                cliente_id=client.id if client.id else None,
                permitir_checkin_global=True,
                habilitar_feedback=True,
                habilitar_certificado_individual=True
            )
            db.session.add(config)
            
            print(f"✅ Client {data['nome']} created")
        else:
            clients.append(client)
    
    db.session.commit()  # Commit to get IDs for clients
    
    # Create Events for each client
    events = []
    for client in clients:
        event_names = [
            f"Annual Training {client.nome} 2025",
            f"Professional Development Workshop {client.nome}",
            f"Specialized Course {client.nome}"
        ]
        
        for name in event_names:
            event = Evento.query.filter_by(nome=name).first()
            if not event:
                event = Evento(
                    cliente_id=client.id,
                    nome=name,
                    descricao=f"A complete event for professional development with multiple workshops and activities. {random_string(50)}",
                    programacao=f"Day 1: Opening\nDay 2: Workshops\nDay 3: Closing and Certificates\n{random_string(100)}",
                    localizacao=f"Convention Center, {random.choice(['São Paulo', 'Rio de Janeiro', 'Belo Horizonte'])}",
                    link_mapa="https://maps.google.com/?q=Convention+Center",
                    inscricao_gratuita=not client.habilita_pagamento
                )
                db.session.add(event)
                events.append(event)
                print(f"✅ Event {name} created for client {client.nome}")
    
    db.session.commit()  # Commit to get IDs for events

    # Create Ministrantes (instructors)
    ministrantes = []
    for i in range(10):
        email = f"ministrante{i+1}@example.com"
        ministrante = Ministrante.query.filter_by(email=email).first()
        if not ministrante:
            ministrante = Ministrante(
                nome=f"Ministrante {i+1}",
                formacao=random.choice(["Ph.D.", "Master", "Specialist", "Bachelor"]),
                categorias_formacao=",".join(random.sample(["Bacharelado", "Licenciatura", "Tecnólogo", "Especialização", "MBA", "Mestrado", "Doutorado"], k=2)),
                areas_atuacao=random.choice(["Education", "Technology", "Science", "Arts", "Business"]),
                cpf=random_cpf(),
                pix=f"pix{i+1}@example.com",
                cidade=random.choice(["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador"]),
                estado=random.choice(["SP", "RJ", "MG", "BA"]),
                email=email,
                senha=generate_password_hash("ministrante123"),
                cliente_id=random.choice(clients).id
            )
            db.session.add(ministrante)
            ministrantes.append(ministrante)
            print(f"✅ Ministrante {email} created")
        else:
            ministrantes.append(ministrante)

    db.session.commit()  # Commit to get IDs for ministrantes

    # Create Oficinas (workshops)
    oficinas = []
    oficina_titles = [
        "Python Programming Basics", "Advanced JavaScript", "Data Science Introduction",
        "Web Development Fundamentals", "Mobile App Development", "Cloud Computing",
        "Artificial Intelligence", "Machine Learning", "Cybersecurity Essentials",
        "DevOps Practices", "Agile Methodology", "UX/UI Design", "Digital Marketing",
        "Project Management", "Blockchain Technology", "IoT Applications",
        "Business Intelligence", "Big Data Analytics", "Game Development",
        "Software Testing", "Network Administration", "Database Management"
    ]
    
    for i, title in enumerate(oficina_titles):
        # Assign to random client and event
        client = random.choice(clients)
        event = random.choice([e for e in events if e.cliente_id == client.id])
        
        oficina = Oficina.query.filter_by(titulo=title).first()
        if not oficina:
            oficina = Oficina(
                titulo=title,
                descricao=f"This workshop covers {title} topics in depth. {random_string(100)}",
                ministrante_id=random.choice(ministrantes).id,
                vagas=random.randint(15, 50),
                carga_horaria=str(random.randint(4, 40)),
                estado=random.choice(["SP", "RJ", "MG", "BA"]),
                cidade=random.choice(["São Paulo", "Rio de Janeiro", "Belo Horizonte", "Salvador"]),
                cliente_id=client.id,
                evento_id=event.id,
                opcoes_checkin="option1,option2,option3,option4,correctoption",
                palavra_correta="correctoption"
            )
            db.session.add(oficina)
            
            # Add 1-3 days to each Oficina
            num_days = random.randint(1, 3)
            for j in range(num_days):
                workshop_date = random_future_date()
                start_time, end_time = random_time_range()
                
                oficina_dia = OficinaDia(
                    oficina_id=oficina.id if oficina.id else None,
                    data=workshop_date,
                    horario_inicio=start_time,
                    horario_fim=end_time
                )
                db.session.add(oficina_dia)
                
            oficinas.append(oficina)
            print(f"✅ Oficina {title} created with {num_days} days")
    
    db.session.commit()  # Commit to get IDs for oficinas

    # Create Participantes (participants)
    participantes = []
    for i in range(30):
        email = f"participant{i+1}@example.com"
        participante = Usuario.query.filter_by(email=email).first()
        if not participante:
            cliente_id = random.choice(clients).id
            participante = Usuario(
                nome=f"Participant {i+1}",
                cpf=random_cpf(),
                email=email,
                senha=generate_password_hash("participant123"),
                formacao=random.choice(["Student", "Professional", "Teacher", "Researcher"]),
                tipo="participante",
                cliente_id=cliente_id,
                estados="SP,RJ",
                cidades="São Paulo,Rio de Janeiro"
            )
            db.session.add(participante)
            participantes.append(participante)
            print(f"✅ Participant {email} created")
        else:
            participantes.append(participante)
    
    db.session.commit()  # Commit to get IDs for participantes

    # Create Inscrições (registrations)
    for i in range(100):  # Creating 100 random inscriptions
        participante = random.choice(participantes)
        oficina = random.choice(oficinas)
        
        # Check if the inscription already exists
        existing_inscription = Inscricao.query.filter_by(
            usuario_id=participante.id, 
            oficina_id=oficina.id
        ).first()
        
        if not existing_inscription and oficina.vagas > 0:
            inscricao = Inscricao(
                usuario_id=participante.id,
                oficina_id=oficina.id,
                cliente_id=oficina.cliente_id
            )
            oficina.vagas -= 1
            
            # Create check-in for half of the inscriptions
            if random.choice([True, False]):
                checkin = Checkin(
                    usuario_id=participante.id,
                    oficina_id=oficina.id,
                    data_hora=datetime.now() - timedelta(days=random.randint(1, 10)),
                    palavra_chave=random.choice(["correctoption", "QR-AUTO"])
                )
                db.session.add(checkin)
                
                # Create feedback for some check-ins
                if random.choice([True, False, False]):
                    feedback = Feedback(
                        usuario_id=participante.id,
                        oficina_id=oficina.id,
                        rating=random.randint(1, 5),
                        comentario=f"This workshop was {'great' if random.choice([True, False]) else 'good'}. {random_string(50)}"
                    )
                    db.session.add(feedback)
            
            db.session.add(inscricao)
            print(f"✅ Inscription created: Participant {participante.nome} in Workshop {oficina.titulo}")
    
    # Create Formulários (forms)
    for client in clients:
        formnames = ["Feedback Form", "Registration Form", "Evaluation Form"]
        
        for formname in formnames:
            formulario = Formulario.query.filter_by(nome=f"{formname} - {client.nome}").first()
            if not formulario:
                formulario = Formulario(
                    nome=f"{formname} - {client.nome}",
                    descricao=f"This form is used to collect {formname.lower()} from participants. {random_string(50)}",
                    cliente_id=client.id
                )
                db.session.add(formulario)
                db.session.flush()  # Get the ID without committing
                
                # Add fields to the form
                campos = [
                    {"nome": "Full Name", "tipo": "text", "obrigatorio": True},
                    {"nome": "Email", "tipo": "text", "obrigatorio": True},
                    {"nome": "Rating", "tipo": "dropdown", "opcoes": "1,2,3,4,5", "obrigatorio": True},
                    {"nome": "Comments", "tipo": "textarea", "obrigatorio": False},
                    {"nome": "Suggestions", "tipo": "textarea", "obrigatorio": False},
                    {"nome": "Upload Document", "tipo": "file", "obrigatorio": False}
                ]
                
                for campo_data in campos:
                    campo = CampoFormulario(
                        formulario_id=formulario.id,
                        nome=campo_data["nome"],
                        tipo=campo_data["tipo"],
                        opcoes=campo_data.get("opcoes", None),
                        obrigatorio=campo_data["obrigatorio"]
                    )
                    db.session.add(campo)
                
                # Add some responses to the form
                for i in range(5):  # 5 responses per form
                    participante = random.choice(participantes)
                    
                    if participante.cliente_id == client.id:  # Only if participant belongs to the client
                        resposta = RespostaFormulario(
                            formulario_id=formulario.id,
                            usuario_id=participante.id,
                            data_submissao=datetime.now() - timedelta(days=random.randint(1, 30)),
                            status_avaliacao=random.choice(["Não Avaliada", "Aprovada", "Aprovada com ressalvas", "Negada"])
                        )
                        db.session.add(resposta)
                        db.session.flush()  # Get the ID without committing
                        
                        # Add field responses
                        for campo in formulario.campos:
                            if campo.tipo == "text":
                                valor = f"{random_string(10)}"
                            elif campo.tipo == "textarea":
                                valor = f"{random_string(50)}"
                            elif campo.tipo == "dropdown":
                                opcoes = campo.opcoes.split(",")
                                valor = random.choice(opcoes)
                            elif campo.tipo == "file":
                                valor = "uploads/respostas/example_file.pdf"
                            else:
                                valor = "sample response"
                                
                            resposta_campo = RespostaCampo(
                                resposta_formulario_id=resposta.id,
                                campo_id=campo.id,
                                valor=valor
                            )
                            db.session.add(resposta_campo)
                
                print(f"✅ Form {formname} created for {client.nome} with fields and responses")

    # Create registration links for events
    for event in events:
        link = LinkCadastro(
            cliente_id=event.cliente_id,
            evento_id=event.id,
            slug_customizado=f"register-{event.id}",
            token=f"token-{event.id}"
        )
        db.session.add(link)
        print(f"✅ Registration link created for event {event.nome}")

    # Add materials to some workshops
    for oficina in oficinas[:5]:  # Just for the first 5 workshops
        material = MaterialOficina(
            oficina_id=oficina.id,
            nome_arquivo=f"material_{oficina.id}.pdf",
            caminho_arquivo=f"uploads/materiais/material_{oficina.id}.pdf"
        )
        db.session.add(material)
        
        # Create mock file
        file_path = f"uploads/materiais/material_{oficina.id}.pdf"
        create_directory_if_not_exists(file_path)
        with open(file_path, 'w') as f:
            f.write("This is a sample material file.")
        
        print(f"✅ Material added for workshop {oficina.titulo}")

    # Add reports to some workshops
    for oficina in oficinas[:5]:  # Just for the first 5 workshops
        ministrante = Ministrante.query.get(oficina.ministrante_id)
        
        if ministrante:
            relatorio = RelatorioOficina(
                oficina_id=oficina.id,
                ministrante_id=ministrante.id,
                metodologia=f"We used an engaging methodology for this workshop. {random_string(100)}",
                resultados=f"The results were satisfactory, with over 90% satisfaction. {random_string(100)}"
            )
            db.session.add(relatorio)
            print(f"✅ Report added for workshop {oficina.titulo}")
    
    # Final commit
    try:
        db.session.commit()
        print("✅ All data committed successfully")
    except IntegrityError as e:
        db.session.rollback()
        print(f"❌ Error during commit: {str(e)}")
        
    print("🎉 Database population completed!")

# Run the script
if __name__ == "__main__":
    with app.app_context():
        populate_database()