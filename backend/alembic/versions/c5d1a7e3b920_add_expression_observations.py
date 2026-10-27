"""add question_expression_observations: optional camera expression counts per answered question

Revision ID: c5d1a7e3b920
Revises: b4c8e2d9f013
Create Date: 2026-10-04 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5d1a7e3b920'
down_revision: Union[str, Sequence[str], None] = 'b4c8e2d9f013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COUNTS = ('neutral', 'happy', 'sad', 'angry', 'fearful', 'disgusted', 'surprised', 'no_face',
          'multiple_faces')
TABLE = 'question_expression_observations'


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        TABLE,
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.Enum('ANALYZED', 'UNAVAILABLE', name='status', native_enum=False,
                                    create_constraint=True, length=20), nullable=False),
        *(sa.Column(name, sa.Integer(), nullable=False) for name in COUNTS),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                  nullable=False),
        *(sa.CheckConstraint(f'{name} BETWEEN 0 AND 10000', name=op.f(f'ck_{TABLE}_{name}_range'))
          for name in COUNTS),
        sa.CheckConstraint(
            "status = 'ANALYZED' OR (neutral + happy + sad + angry + fearful + disgusted + "
            "surprised + no_face + multiple_faces) = 0",
            name=op.f(f'ck_{TABLE}_unavailable_has_no_counts')),
        sa.ForeignKeyConstraint(['question_id'], ['interview_questions.id'],
                                name=op.f(f'fk_{TABLE}_question_id_interview_questions'),
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('question_id', name=op.f(f'pk_{TABLE}')),
    )


def downgrade() -> None:
    """Downgrade schema. Refuses while any observation exists: the older schema cannot hold
    them and dropping them would silently change those reports. Delete those interviews first,
    or stay on this revision."""
    count = op.get_bind().scalar(sa.text(f"SELECT count(*) FROM {TABLE}"))
    if count:
        raise RuntimeError(
            f"Refusing to downgrade: {count} expression observation(s) exist, which the older "
            "schema cannot represent. Delete those interview sessions first, or stay on this "
            "revision.")
    op.drop_table(TABLE)
