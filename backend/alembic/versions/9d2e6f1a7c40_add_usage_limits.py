"""add usage limits: usage_counters and the QUOTA_REACHED rules reason

Revision ID: 9d2e6f1a7c40
Revises: 70b0b7891bc0
Create Date: 2026-10-03 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d2e6f1a7c40'
down_revision: Union[str, Sequence[str], None] = '70b0b7891bc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Hand-written, like the earlier revisions: autogenerate does not compare CHECK contents.
OLD_REASONS = ("'NOT_REQUESTED', 'NOT_CONFIGURED', 'PROVIDERS_FAILED', 'OUTPUT_REJECTED', "
               "'CONSENT_WITHDRAWN'")
NEW_REASONS = f"{OLD_REASONS}, 'QUOTA_REACHED'"
TABLES = ('interview_questions', 'answer_evaluations')


def _reason_checks(reasons: str) -> None:
    for table in TABLES:
        name = op.f(f'ck_{table}_rules_reason')
        op.drop_constraint(name, table, type_='check')
        op.create_check_constraint(name, table, f"rules_reason IN ({reasons})")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'usage_counters',
        sa.Column('scope', sa.String(length=40), nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('count >= 1', name=op.f('ck_usage_counters_count_positive')),
        sa.PrimaryKeyConstraint('scope', 'key', 'window_start', name=op.f('pk_usage_counters')),
    )
    op.create_index(op.f('ix_usage_counters_expires_at'), 'usage_counters', ['expires_at'])
    _reason_checks(NEW_REASONS)


def downgrade() -> None:
    """Downgrade schema.

    Counters are only short-lived operational state, so they are dropped. Refuses while a
    question or evaluation carries QUOTA_REACHED: none of the older reasons is true for it.
    Delete those interview sessions first, or stay on this revision.
    """
    bind = op.get_bind()
    count = sum(bind.scalar(sa.text(
        f"SELECT count(*) FROM {table} WHERE rules_reason = 'QUOTA_REACHED'")) for table in TABLES)
    if count:
        raise RuntimeError(
            f"Refusing to downgrade: {count} question(s) or evaluation(s) used the deterministic "
            "path because of QUOTA_REACHED, which the older schema cannot represent. Delete "
            "those interview sessions first, or stay on this revision.")
    _reason_checks(OLD_REASONS)
    op.drop_index(op.f('ix_usage_counters_expires_at'), table_name='usage_counters')
    op.drop_table('usage_counters')
