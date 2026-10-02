"""add answer evaluations (Phase 8 evaluator)

Revision ID: 3a4785ecf08e
Revises: 3871903c395d
Create Date: 2026-10-02 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3a4785ecf08e'
down_revision: Union[str, Sequence[str], None] = '3871903c395d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Hand-written, like the earlier revisions: autogenerate does not compare CHECK contents.
OLD_CAPABILITIES = "'PROFILE_EXTRACTION', 'INTERVIEW_PLANNING', 'QUESTION_GENERATION'"
NEW_CAPABILITIES = f"{OLD_CAPABILITIES}, 'ANSWER_EVALUATION'"
CAPABILITY_CHECK = 'ck_provider_calls_capability'
OLD_STATUSES = "'NOT_EVALUATED'"
NEW_STATUSES = "'NOT_EVALUATED', 'NOT_APPLICABLE', 'OBSERVATIONS_ONLY', 'EVALUATED'"
STATUS_CHECK = 'ck_interview_questions_evaluation_status'
RULES_REASONS = ("'NOT_REQUESTED', 'NOT_CONFIGURED', 'PROVIDERS_FAILED', 'OUTPUT_REJECTED', "
                 "'CONSENT_WITHDRAWN'")
CRITERIA = ("'relevance', 'completeness', 'reasoning', 'communication', 'structure', "
            "'specificity', 'evidence', 'reflection', 'outcome'")


def _replace_check(table: str, name: str, condition: str) -> None:
    op.drop_constraint(op.f(name), table, type_='check')
    op.create_check_constraint(op.f(name), table, condition)


def upgrade() -> None:
    """Upgrade schema. Existing answers stay NOT_EVALUATED: nothing is evaluated retroactively."""
    _replace_check('provider_calls', CAPABILITY_CHECK, f"capability IN ({NEW_CAPABILITIES})")
    _replace_check('interview_questions', STATUS_CHECK, f"evaluation_status IN ({NEW_STATUSES})")

    op.create_table(
        'answer_evaluations',
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('rubric', sa.String(length=20), nullable=False),
        sa.Column('rubric_version', sa.SmallInteger(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('rules_reason', sa.String(length=20), nullable=True),
        sa.Column('attempts', sa.SmallInteger(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('concepts_mentioned', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('missing_concepts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('claims_to_verify', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('feedback', sa.Text(), nullable=True),
        sa.Column('provider_call_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.CheckConstraint("rubric IN ('TECHNICAL_PROJECT', 'BEHAVIORAL_HR')",
                           name=op.f('ck_answer_evaluations_rubric')),
        sa.CheckConstraint("source IN ('AI', 'RULES')", name=op.f('ck_answer_evaluations_source')),
        sa.CheckConstraint(f"rules_reason IN ({RULES_REASONS})",
                           name=op.f('ck_answer_evaluations_rules_reason')),
        sa.CheckConstraint("(source = 'AI') = (rules_reason IS NULL)",
                           name=op.f('ck_answer_evaluations_rules_reason_matches_source')),
        sa.CheckConstraint('rubric_version >= 1',
                           name=op.f('ck_answer_evaluations_rubric_version_positive')),
        sa.CheckConstraint('attempts BETWEEN 1 AND 2',
                           name=op.f('ck_answer_evaluations_attempts_range')),
        sa.CheckConstraint('word_count >= 0',
                           name=op.f('ck_answer_evaluations_word_count_not_negative')),
        sa.CheckConstraint('char_length(feedback) <= 600',
                           name=op.f('ck_answer_evaluations_feedback_length')),
        sa.CheckConstraint(
            "jsonb_typeof(concepts_mentioned) = 'array' AND jsonb_typeof(missing_concepts) = "
            "'array' AND jsonb_typeof(claims_to_verify) = 'array'",
            name=op.f('ck_answer_evaluations_lists_are_arrays')),
        sa.CheckConstraint(
            "source = 'AI' OR (feedback IS NULL AND missing_concepts = '[]'::jsonb "
            "AND claims_to_verify = '[]'::jsonb)",
            name=op.f('ck_answer_evaluations_rules_has_no_model_content')),
        sa.ForeignKeyConstraint(['question_id'], ['interview_questions.id'],
                                name=op.f('fk_answer_evaluations_question_id_interview_questions'),
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['provider_call_id'], ['provider_calls.id'],
                                name=op.f('fk_answer_evaluations_provider_call_id_provider_calls'),
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('question_id', name=op.f('pk_answer_evaluations')),
    )
    op.create_table(
        'answer_evaluation_criteria',
        sa.Column('question_id', sa.Uuid(), nullable=False),
        sa.Column('criterion', sa.String(length=20), nullable=False),
        sa.Column('score', sa.SmallInteger(), nullable=True),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(f"criterion IN ({CRITERIA})",
                           name=op.f('ck_answer_evaluation_criteria_criterion')),
        sa.CheckConstraint('score BETWEEN 1 AND 5',
                           name=op.f('ck_answer_evaluation_criteria_score_range')),
        sa.CheckConstraint("jsonb_typeof(evidence) = 'array'",
                           name=op.f('ck_answer_evaluation_criteria_evidence_is_array')),
        sa.CheckConstraint('score IS NULL OR jsonb_array_length(evidence) >= 1',
                           name=op.f('ck_answer_evaluation_criteria_score_needs_evidence')),
        sa.ForeignKeyConstraint(
            ['question_id'], ['answer_evaluations.question_id'],
            name=op.f('fk_answer_evaluation_criteria_question_id_answer_evaluations'),
            ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('question_id', 'criterion',
                                name=op.f('pk_answer_evaluation_criteria')),
    )


def downgrade() -> None:
    """Downgrade schema.

    Refuses while any evaluation is stored, or any answer has a status other than NOT_EVALUATED:
    the older schema cannot hold them, and dropping them would silently lose them. Evaluation call
    metadata (provider_calls rows with no prompt, output or candidate link) is deleted, since the
    older CHECK cannot hold it.
    """
    bind = op.get_bind()
    evaluations = bind.scalar(sa.text("SELECT count(*) FROM answer_evaluations"))
    statuses = bind.scalar(sa.text("SELECT count(*) FROM interview_questions "
                                   "WHERE evaluation_status <> 'NOT_EVALUATED'"))
    if evaluations or statuses:
        raise RuntimeError(
            f"Refusing to downgrade: {evaluations} answer evaluation(s) are stored and "
            f"{statuses} answer(s) have an evaluation status, which this downgrade would lose. "
            "Delete those sessions first, or stay on this revision.")
    op.drop_table('answer_evaluation_criteria')
    op.drop_table('answer_evaluations')
    _replace_check('interview_questions', STATUS_CHECK, f"evaluation_status IN ({OLD_STATUSES})")
    op.execute("DELETE FROM provider_calls WHERE capability = 'ANSWER_EVALUATION'")
    _replace_check('provider_calls', CAPABILITY_CHECK, f"capability IN ({OLD_CAPABILITIES})")
