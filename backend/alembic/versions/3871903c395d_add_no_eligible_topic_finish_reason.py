"""add NO_ELIGIBLE_TOPIC finish reason

Revision ID: 3871903c395d
Revises: 178659f38d45
Create Date: 2026-10-02 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3871903c395d'
down_revision: Union[str, Sequence[str], None] = '178659f38d45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD = "'PLAN_COMPLETED', 'TIME_LIMIT', 'CANDIDATE_ENDED'"
NEW = f"{OLD}, 'NO_ELIGIBLE_TOPIC'"
NAME = 'ck_interview_sessions_finish_reason'  # used via op.f: final name, no naming convention


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(op.f(NAME), 'interview_sessions', type_='check')
    op.create_check_constraint(op.f(NAME), 'interview_sessions', f"finish_reason IN ({NEW})")


def downgrade() -> None:
    """Downgrade schema.

    Refuses while a session finished with NO_ELIGIBLE_TOPIC: none of the older reasons is true for
    it (its plan was not completed, the time did not run out, the candidate did not end it), and
    dropping it to NULL would lose why it ended. Delete those sessions first, or stay on this
    revision.
    """
    count = op.get_bind().scalar(sa.text(
        "SELECT count(*) FROM interview_sessions WHERE finish_reason = 'NO_ELIGIBLE_TOPIC'"))
    if count:
        raise RuntimeError(
            f"Refusing to downgrade: {count} interview session(s) finished with NO_ELIGIBLE_TOPIC, "
            "which the older schema cannot represent. Delete those sessions first, or stay on "
            "this revision.")
    op.drop_constraint(op.f(NAME), 'interview_sessions', type_='check')
    op.create_check_constraint(op.f(NAME), 'interview_sessions', f"finish_reason IN ({OLD})")
