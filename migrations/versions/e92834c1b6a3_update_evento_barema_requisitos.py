"""store min and max in EventoBarema.requisitos

Revision ID: e92834c1b6a3
Revises: 97ff1ac3c1dc
Create Date: 2025-08-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
import json


# revision identifiers, used by Alembic.
revision = "e92834c1b6a3"
down_revision = "97ff1ac3c1dc"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, requisitos FROM evento_barema"))
    for row in rows:
        reqs = row.requisitos or {}
        new_reqs = {}
        for key, value in reqs.items():
            if isinstance(value, dict) and {"min", "max"} <= value.keys():
                new_reqs[key] = value
            else:
                new_reqs[key] = {"min": 0, "max": value}
        conn.execute(
            sa.text(
                "UPDATE evento_barema SET requisitos = :reqs WHERE id = :id"
            ),
            {"id": row.id, "reqs": json.dumps(new_reqs)},
        )


def downgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, requisitos FROM evento_barema"))
    for row in rows:
        reqs = row.requisitos or {}
        old_reqs = {}
        for key, value in reqs.items():
            if isinstance(value, dict) and "max" in value:
                old_reqs[key] = value["max"]
            else:
                old_reqs[key] = value
        conn.execute(
            sa.text(
                "UPDATE evento_barema SET requisitos = :reqs WHERE id = :id"
            ),
            {"id": row.id, "reqs": json.dumps(old_reqs)},
        )

