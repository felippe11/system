from .user import *  # noqa: F401,F403
from .event import *  # noqa: F401,F403
from .review import *  # noqa: F401,F403

# Importações explícitas para garantir disponibilidade
from .event import ParticipanteEvento, MonitorAgendamento, PresencaAluno, MaterialApoio, NecessidadeEspecial
from .user import Monitor

