"""create resumes and candidate_facts tables

Revision ID: c7292e1e2002
Revises: e3b2e5da06bf
Create Date: 2026-09-28 04:13:19.556744

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c7292e1e2002'
down_revision: Union[str, Sequence[str], None] = 'e3b2e5da06bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Status/category columns are VARCHAR + one named CHECK each (the models use non-native Enums).
# Autogenerate emitted every CHECK twice; this is the hand-corrected version.


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('resumes',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('candidate_id', sa.Uuid(), nullable=False),
    sa.Column('raw_text', sa.Text(), nullable=True),
    sa.Column('parsed_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('upload_status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("upload_status IN ('PROCESSED', 'FAILED', 'UNSUPPORTED')", name=op.f('ck_resumes_upload_status')),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name=op.f('fk_resumes_candidate_id_candidates'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resumes')),
    sa.UniqueConstraint('id', 'candidate_id', name='uq_resumes_id_candidate_id')
    )
    op.create_index(op.f('ix_resumes_candidate_id'), 'resumes', ['candidate_id'], unique=False)
    op.create_table('candidate_facts',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('candidate_id', sa.Uuid(), nullable=False),
    sa.Column('resume_id', sa.Uuid(), nullable=False),
    sa.Column('category', sa.String(length=20), nullable=False),
    sa.Column('fact', sa.String(length=200), nullable=False),
    sa.Column('extracted_fact', sa.String(length=200), nullable=False),
    sa.Column('source', sa.String(length=20), nullable=False),
    sa.Column('source_section', sa.String(length=100), nullable=False),
    sa.Column('source_text', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=20), server_default='PENDING_REVIEW', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("btrim(extracted_fact) <> ''", name=op.f('ck_candidate_facts_extracted_fact_not_blank')),
    sa.CheckConstraint("btrim(fact) <> ''", name=op.f('ck_candidate_facts_fact_not_blank')),
    sa.CheckConstraint("category IN ('SKILL', 'PROJECT', 'EXPERIENCE', 'EDUCATION', 'CERTIFICATION')", name=op.f('ck_candidate_facts_category')),
    sa.CheckConstraint("source IN ('RESUME')", name=op.f('ck_candidate_facts_source')),
    sa.CheckConstraint("status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED')", name=op.f('ck_candidate_facts_status')),
    sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], name=op.f('fk_candidate_facts_candidate_id_candidates'), ondelete='CASCADE'),
    # Composite FK: a fact always belongs to the same candidate as its resume.
    sa.ForeignKeyConstraint(['resume_id', 'candidate_id'], ['resumes.id', 'resumes.candidate_id'], name=op.f('fk_candidate_facts_resume_id_resumes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_candidate_facts'))
    )
    op.create_index(op.f('ix_candidate_facts_candidate_id'), 'candidate_facts', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_candidate_facts_resume_id'), 'candidate_facts', ['resume_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_candidate_facts_resume_id'), table_name='candidate_facts')
    op.drop_index(op.f('ix_candidate_facts_candidate_id'), table_name='candidate_facts')
    op.drop_table('candidate_facts')
    op.drop_index(op.f('ix_resumes_candidate_id'), table_name='resumes')
    op.drop_table('resumes')
