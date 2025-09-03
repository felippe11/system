"""Merge multiple heads

Revision ID: 6570f4d24eff
Revises: 107bbecb438c, add_trabalho_id_resposta, b04a661b724f, e89dc0a9d598, fix_assignment_foreign_keys
Create Date: 2025-09-02 18:00:58.062930

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6570f4d24eff'
down_revision = ('107bbecb438c', 'add_trabalho_id_resposta', 'b04a661b724f', 'e89dc0a9d598', 'fix_assignment_foreign_keys')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
