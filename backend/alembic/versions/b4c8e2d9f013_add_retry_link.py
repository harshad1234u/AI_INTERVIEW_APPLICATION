"""add retry link: interview_sessions.retry_of_id, for the candidate's interview history

Revision ID: b4c8e2d9f013
Revises: 9d2e6f1a7c40
Create Date: 2026-10-03 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c8e2d9f013'
down_revision: Union[str, Sequence[str], None] = '9d2e6f1a7c40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. Existing retries stay unlinked: which session they retried was never
    stored, and guessing it would invent history."""
    op.add_column('interview_sessions', sa.Column('retry_of_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(op.f('fk_interview_sessions_retry_of_id_interview_sessions'),
                          'interview_sessions', 'interview_sessions', ['retry_of_id'], ['id'],
                          ondelete='SET NULL')
    op.create_index(op.f('ix_interview_sessions_retry_of_id'), 'interview_sessions',
                    ['retry_of_id'])
    op.create_check_constraint(op.f('ck_interview_sessions_retry_of_another_session'),
                               'interview_sessions', 'retry_of_id <> id')


def downgrade() -> None:
    """Downgrade schema. Refuses while any retry is linked to its source: the older schema
    cannot hold the link, and dropping it would lose the candidate's history. Delete those
    retries first, or stay on this revision."""
    count = op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM interview_sessions WHERE retry_of_id IS NOT NULL"))
    if count:
        raise RuntimeError(
            f"Refusing to downgrade: {count} interview session(s) are linked to the interview "
            "they retry, which the older schema cannot represent. Delete those sessions first, "
            "or stay on this revision.")
    op.drop_constraint(op.f('ck_interview_sessions_retry_of_another_session'),
                       'interview_sessions', type_='check')
    op.drop_index(op.f('ix_interview_sessions_retry_of_id'), table_name='interview_sessions')
    op.drop_constraint(op.f('fk_interview_sessions_retry_of_id_interview_sessions'),
                       'interview_sessions', type_='foreignkey')
    op.drop_column('interview_sessions', 'retry_of_id')
