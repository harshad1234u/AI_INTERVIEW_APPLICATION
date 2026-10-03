"""add manual facts (Phase 13): MANUAL source with no resume provenance

Revision ID: 70b0b7891bc0
Revises: 5c0e1d2f7a91
Create Date: 2026-10-03 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70b0b7891bc0'
down_revision: Union[str, Sequence[str], None] = '5c0e1d2f7a91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Hand-written, like the earlier revisions: autogenerate compares neither CHECK contents nor
# expression indexes.
SOURCE_CHECK = 'ck_candidate_facts_source'
PROVENANCE_CHECK = 'ck_candidate_facts_provenance_matches_source'
PROVENANCE = (
    "(source = 'MANUAL' AND resume_id IS NULL AND source_section IS NULL "
    "AND source_text IS NULL AND extracted_by IS NULL AND provider_call_id IS NULL "
    "AND status = 'APPROVED') OR "
    "(source <> 'MANUAL' AND resume_id IS NOT NULL AND source_section IS NOT NULL "
    "AND source_text IS NOT NULL AND extracted_by IS NOT NULL)"
)
UNIQUE_INDEX = 'uq_candidate_facts_manual_fact'
OPTIONAL = [('resume_id', sa.Uuid()), ('source_section', sa.String(length=100)),
            ('source_text', sa.Text()), ('extracted_by', sa.String(length=20))]


def upgrade() -> None:
    """Upgrade schema. Every existing fact is a resume fact and already satisfies the new CHECK."""
    op.drop_constraint(op.f(SOURCE_CHECK), 'candidate_facts', type_='check')
    op.create_check_constraint(op.f(SOURCE_CHECK), 'candidate_facts',
                               "source IN ('RESUME', 'MANUAL')")
    for column, type_ in OPTIONAL:
        op.alter_column('candidate_facts', column, existing_type=type_, nullable=True)
    op.create_check_constraint(op.f(PROVENANCE_CHECK), 'candidate_facts', PROVENANCE)
    op.create_index(UNIQUE_INDEX, 'candidate_facts',
                    ['candidate_id', 'category', sa.text('lower(fact)')], unique=True,
                    postgresql_where=sa.text("source = 'MANUAL'"))


def downgrade() -> None:
    """Downgrade schema.

    Refuses while any manual fact exists: the older schema requires resume provenance, and
    dropping them would silently delete what the candidate typed in (and change their plans).
    """
    bind = op.get_bind()
    manual = bind.scalar(sa.text("SELECT count(*) FROM candidate_facts WHERE source = 'MANUAL'"))
    if manual:
        raise RuntimeError(
            f"Refusing to downgrade: {manual} manual fact(s) exist, which this downgrade would "
            "lose. Delete them first, or stay on this revision.")
    op.drop_index(UNIQUE_INDEX, table_name='candidate_facts')
    op.drop_constraint(op.f(PROVENANCE_CHECK), 'candidate_facts', type_='check')
    for column, type_ in OPTIONAL:
        op.alter_column('candidate_facts', column, existing_type=type_, nullable=False)
    op.drop_constraint(op.f(SOURCE_CHECK), 'candidate_facts', type_='check')
    op.create_check_constraint(op.f(SOURCE_CHECK), 'candidate_facts', "source IN ('RESUME')")
