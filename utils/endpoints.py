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
