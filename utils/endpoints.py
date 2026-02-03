"""Centralized Flask endpoint names for dashboard pages.

This module defines constants for dashboard-related endpoints used across the
application. Import these constants instead of hard-coding strings so updates to
endpoint names can be made in one place.
"""

DASHBOARD = "dashboard_routes.dashboard"
"""Endpoint for the general dashboard."""

DASHBOARD_CLIENTE = "dashboard_routes.dashboard_cliente"
"""Endpoint for the client dashboard."""

DASHBOARD_ADMIN = "dashboard_routes.dashboard_admin"
"""Endpoint for the admin dashboard."""

DASHBOARD_SUPERADMIN = "dashboard_routes.dashboard_superadmin"
"""Endpoint for the superadmin dashboard."""

DASHBOARD_AGENDAMENTOS = "dashboard_routes.dashboard_agendamentos"
"""Endpoint for the scheduling dashboard."""

DASHBOARD_PARTICIPANTE = "dashboard_participante_routes.dashboard_participante"
"""Endpoint for the participant dashboard."""

DASHBOARD_REVISOR = "peer_review_routes.reviewer_dashboard"
"""Endpoint for the reviewer dashboard."""

DASHBOARD_CLIENTE_PERMISSOES_ATIVIDADES = (
    "dashboard_routes.configurar_permissoes_atividades"
)
"""Endpoint for managing activity permissions by subscription type."""

DASHBOARD_CLIENTE_GERENCIAR_VAGAS = (
    "dashboard_routes.gerenciar_vagas_atividades"
)
"""Endpoint for managing workshop vacancies in the client dashboard."""
