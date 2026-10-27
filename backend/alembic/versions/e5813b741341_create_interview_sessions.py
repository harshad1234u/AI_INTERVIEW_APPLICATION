"""create interview_sessions

Revision ID: e5813b741341
Revises: a41f0c9e7b25
Create Date: 2026-10-01 11:40:53.630792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5813b741341'
down_revision: Union[str, Sequence[str], None] = 'a41f0c9e7b25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Hand-corrected like c7292e1e2002: the status column is VARCHAR + one named CHECK
# (autogenerate emitted the CHECK twice).
STATUSES = ("'CREATED', 'PROFILE_PROCESSING', 'PROFILE_REVIEW', 'INTERVIEW_PLANNING', 'READY', "
            "'ASKING', 'WAITING_FOR_ANSWER', 'PAUSED', 'ANSWER_PROCESSING', 'ANSWER_EVALUATION', "
            "'NEXT_DECISION', 'REPORT_GENERATION', 'COMPLETED'")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('interview_sessions',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('candidate_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint(f"status IN ({STATUSES})", name=op.f('ck_interview_sessions_status')),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name=op.f('fk_interview_sessions_candidate_id_candidates'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_interview_sessions'))
    )
    op.create_index(op.f('ix_interview_sessions_candidate_id'), 'interview_sessions', ['candidate_id'], unique=False)
    # At most one unfinished session per candidate.
    op.create_index('uq_interview_sessions_one_active_per_candidate', 'interview_sessions', ['candidate_id'], unique=True, postgresql_where=sa.text("status <> 'COMPLETED'"))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_interview_sessions_one_active_per_candidate', table_name='interview_sessions', postgresql_where=sa.text("status <> 'COMPLETED'"))
    op.drop_index(op.f('ix_interview_sessions_candidate_id'), table_name='interview_sessions')
    op.drop_table('interview_sessions')
