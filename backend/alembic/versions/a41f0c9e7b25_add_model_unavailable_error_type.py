"""add MODEL_UNAVAILABLE provider-call error type

Revision ID: a41f0c9e7b25
Revises: c6cd3fd96db6
Create Date: 2026-10-01 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a41f0c9e7b25'
down_revision: Union[str, Sequence[str], None] = 'c6cd3fd96db6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD = ("'TIMEOUT', 'CONNECTION', 'RATE_LIMITED', 'SERVER_ERROR', 'INVALID_OUTPUT', "
       "'AUTH', 'BAD_REQUEST', 'UNEXPECTED'")
NEW = OLD.replace("'BAD_REQUEST'", "'MODEL_UNAVAILABLE', 'BAD_REQUEST'")
NAME = 'ck_provider_calls_error_type'  # used via op.f: final name, no naming convention


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f(NAME), 'provider_calls', type_='check')
    op.create_check_constraint(op.f(NAME), 'provider_calls', f"error_type IN ({NEW})")


def downgrade() -> None:
    """Downgrade schema."""
    # Before this revision an unknown model (HTTP 404) was recorded as BAD_REQUEST.
    op.execute("UPDATE provider_calls SET error_type = 'BAD_REQUEST' "
               "WHERE error_type = 'MODEL_UNAVAILABLE'")
    op.drop_constraint(op.f(NAME), 'provider_calls', type_='check')
    op.create_check_constraint(op.f(NAME), 'provider_calls', f"error_type IN ({OLD})")
