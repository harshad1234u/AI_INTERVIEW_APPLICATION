"""add interview plan

Revision ID: b8d14f2a9c63
Revises: e5813b741341
Create Date: 2026-10-01 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b8d14f2a9c63'
down_revision: Union[str, Sequence[str], None] = 'e5813b741341'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Hand-written, like a41f0c9e7b25: autogenerate does not compare CHECK constraint contents.
OLD_CAPABILITIES = "'PROFILE_EXTRACTION'"
NEW_CAPABILITIES = "'PROFILE_EXTRACTION', 'INTERVIEW_PLANNING'"
CAPABILITY_CHECK = 'ck_provider_calls_capability'
PRE_PLAN = "'CREATED', 'PROFILE_PROCESSING', 'PROFILE_REVIEW', 'INTERVIEW_PLANNING'"


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f(CAPABILITY_CHECK), 'provider_calls', type_='check')
    op.create_check_constraint(op.f(CAPABILITY_CHECK), 'provider_calls',
                               f"capability IN ({NEW_CAPABILITIES})")
    op.add_column('interview_sessions', sa.Column('plan', postgresql.JSONB(), nullable=True))
    op.add_column('interview_sessions', sa.Column('plan_provider_call_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(op.f('fk_interview_sessions_plan_provider_call_id_provider_calls'),
                          'interview_sessions', 'provider_calls', ['plan_provider_call_id'], ['id'],
                          ondelete='SET NULL')
    # Before this revision no session could get past INTERVIEW_PLANNING, so existing rows satisfy
    # this with plan = NULL. If one somehow did, the upgrade fails here instead of hiding it.
    op.create_check_constraint(op.f('ck_interview_sessions_plan_matches_status'),
                               'interview_sessions',
                               f"(plan IS NOT NULL) = (status NOT IN ({PRE_PLAN}))")
    op.create_check_constraint(op.f('ck_interview_sessions_plan_is_object'), 'interview_sessions',
                               "plan IS NULL OR jsonb_typeof(plan) = 'object'")


def downgrade() -> None:
    """Downgrade schema.

    Refuses while any session has a plan: dropping the column would silently delete it. Delete
    those sessions first (DELETE /api/interview-sessions/{id}) if you really want to go back.
    Planning call metadata (provider_calls rows with no prompt, output or candidate link) is
    deleted, since the older CHECK cannot hold it.
    """
    planned = op.get_bind().scalar(
        sa.text("SELECT count(*) FROM interview_sessions WHERE plan IS NOT NULL"))
    if planned:
        raise RuntimeError(
            f"Refusing to downgrade: {planned} interview session(s) have saved plans that this "
            "downgrade would delete. Delete those sessions first, or stay on this revision.")
    op.drop_constraint(op.f('ck_interview_sessions_plan_is_object'), 'interview_sessions',
                       type_='check')
    op.drop_constraint(op.f('ck_interview_sessions_plan_matches_status'), 'interview_sessions',
                       type_='check')
    op.drop_constraint(op.f('fk_interview_sessions_plan_provider_call_id_provider_calls'),
                       'interview_sessions', type_='foreignkey')
    op.drop_column('interview_sessions', 'plan_provider_call_id')
    op.drop_column('interview_sessions', 'plan')
    op.execute("DELETE FROM provider_calls WHERE capability = 'INTERVIEW_PLANNING'")
    op.drop_constraint(op.f(CAPABILITY_CHECK), 'provider_calls', type_='check')
    op.create_check_constraint(op.f(CAPABILITY_CHECK), 'provider_calls',
                               f"capability IN ({OLD_CAPABILITIES})")
