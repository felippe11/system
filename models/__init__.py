from .user import *  # noqa: F401,F403
from .event import *  # noqa: F401,F403
from .review import *  # noqa: F401,F403
from .certificado import *  # noqa: F401,F403
from .submission_system import (
    SubmissionCategory,
    ReviewerProfile,
    ReviewerPreference,
    DistributionConfig,
    DistributionLog,
    ImportedSubmission,
    SpreadsheetMapping,
)  # noqa: F401
from .material import *  # noqa: F401,F403

# Importações explícitas para garantir disponibilidade
from .event import ParticipanteEvento, MonitorAgendamento, PresencaAluno, MaterialApoio, NecessidadeEspecial
from .user import Monitor
from .certificado import CertificadoConfig, CertificadoParticipante, NotificacaoCertificado, SolicitacaoCertificado, RegraCertificado, CertificadoTemplateAvancado, DeclaracaoTemplate

