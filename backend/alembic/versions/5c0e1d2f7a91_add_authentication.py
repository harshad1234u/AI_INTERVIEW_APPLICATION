"""add authentication (Phase 12): candidate credentials and server-side sessions

Revision ID: 5c0e1d2f7a91
Revises: 3a4785ecf08e
Create Date: 2026-10-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c0e1d2f7a91'
down_revision: Union[str, Sequence[str], None] = '3a4785ecf08e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema. Existing candidates get no password, so they cannot log in (A3)."""
    op.add_column('candidates', sa.Column('password_hash', sa.String(length=200), nullable=True))
    op.add_column('candidates', sa.Column('failed_logins', sa.SmallInteger(),
                                          server_default='0', nullable=False))
    op.add_column('candidates', sa.Column('locked_until', sa.DateTime(timezone=True),
                                          nullable=True))
    op.create_check_constraint(op.f('ck_candidates_failed_logins_not_negative'), 'candidates',
                               'failed_logins >= 0')
    op.create_table(
        'auth_sessions',
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('candidate_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('expires_at > created_at',
                           name=op.f('ck_auth_sessions_expires_after_created')),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'],
                                name=op.f('fk_auth_sessions_candidate_id_candidates'),
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('token_hash', name=op.f('pk_auth_sessions')),
    )
    op.create_index(op.f('ix_auth_sessions_candidate_id'), 'auth_sessions', ['candidate_id'])


def downgrade() -> None:
    """Downgrade schema.

    Refuses while any candidate has a password: the older schema cannot hold it, and dropping it
    would silently lock those candidates out. Sessions are dropped (everyone is signed out).
    """
    bind = op.get_bind()
    passwords = bind.scalar(sa.text("SELECT count(*) FROM candidates "
                                    "WHERE password_hash IS NOT NULL"))
    if passwords:
        raise RuntimeError(
            f"Refusing to downgrade: {passwords} candidate(s) have a password, which this "
            "downgrade would lose. Delete those candidates first, or stay on this revision.")
    op.drop_index(op.f('ix_auth_sessions_candidate_id'), table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_constraint(op.f('ck_candidates_failed_logins_not_negative'), 'candidates',
                       type_='check')
    op.drop_column('candidates', 'locked_until')
    op.drop_column('candidates', 'failed_logins')
    op.drop_column('candidates', 'password_hash')
