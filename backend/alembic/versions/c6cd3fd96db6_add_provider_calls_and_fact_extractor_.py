"""add provider_calls and fact extractor provenance

Revision ID: c6cd3fd96db6
Revises: c7292e1e2002
Create Date: 2026-09-28 05:00:10.256057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6cd3fd96db6'
down_revision: Union[str, Sequence[str], None] = 'c7292e1e2002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Hand-corrected like c7292e1e2002: enum columns are VARCHAR + one named CHECK each
# (autogenerate emitted every CHECK twice).
ERROR_TYPES = ("'TIMEOUT', 'CONNECTION', 'RATE_LIMITED', 'SERVER_ERROR', 'INVALID_OUTPUT', "
               "'AUTH', 'BAD_REQUEST', 'UNEXPECTED'")


def upgrade() -> None:
    """Upgrade schema."""
    # Operational metadata only: no prompts, resume text, model output or candidate link.
    op.create_table('provider_calls',
    sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('request_id', sa.String(length=32), nullable=False),
    sa.Column('capability', sa.String(length=20), nullable=False),
    sa.Column('requested_provider', sa.String(length=20), nullable=False),
    sa.Column('provider', sa.String(length=20), nullable=True),
    sa.Column('model', sa.String(length=200), nullable=True),
    sa.Column('succeeded', sa.Boolean(), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('fallback_used', sa.Boolean(), nullable=False),
    sa.Column('error_type', sa.String(length=20), nullable=True),
    sa.Column('latency_ms', sa.Integer(), nullable=False),
    sa.Column('input_tokens', sa.Integer(), nullable=True),
    sa.Column('output_tokens', sa.Integer(), nullable=True),
    sa.Column('total_tokens', sa.Integer(), nullable=True),
    sa.Column('provider_request_id', sa.String(length=200), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("capability IN ('PROFILE_EXTRACTION')", name=op.f('ck_provider_calls_capability')),
    sa.CheckConstraint(f"error_type IN ({ERROR_TYPES})", name=op.f('ck_provider_calls_error_type')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_provider_calls'))
    )
    op.create_index(op.f('ix_provider_calls_request_id'), 'provider_calls', ['request_id'], unique=False)
    # Existing (Phase 3) facts all came from the rule-based extractor.
    op.add_column('candidate_facts', sa.Column('extracted_by', sa.String(length=20), server_default='RULES', nullable=False))
    op.create_check_constraint(op.f('ck_candidate_facts_extracted_by'), 'candidate_facts', "extracted_by IN ('RULES', 'AI')")
    op.add_column('candidate_facts', sa.Column('provider_call_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(op.f('fk_candidate_facts_provider_call_id_provider_calls'), 'candidate_facts', 'provider_calls', ['provider_call_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('fk_candidate_facts_provider_call_id_provider_calls'), 'candidate_facts', type_='foreignkey')
    op.drop_column('candidate_facts', 'provider_call_id')
    op.drop_constraint(op.f('ck_candidate_facts_extracted_by'), 'candidate_facts', type_='check')
    op.drop_column('candidate_facts', 'extracted_by')
    op.drop_index(op.f('ix_provider_calls_request_id'), table_name='provider_calls')
    op.drop_table('provider_calls')
