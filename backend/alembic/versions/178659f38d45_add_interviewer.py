"""add interviewer: consent, active clock, finish reason, questions and answers

Revision ID: 178659f38d45
Revises: b8d14f2a9c63
Create Date: 2026-10-01 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '178659f38d45'
down_revision: Union[str, Sequence[str], None] = 'b8d14f2a9c63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Hand-written, like b8d14f2a9c63: autogenerate does not compare CHECK constraint contents.
OLD_CAPABILITIES = "'PROFILE_EXTRACTION', 'INTERVIEW_PLANNING'"
NEW_CAPABILITIES = "'PROFILE_EXTRACTION', 'INTERVIEW_PLANNING', 'QUESTION_GENERATION'"
CAPABILITY_CHECK = 'ck_provider_calls_capability'
RULES_REASONS = ("'NOT_REQUESTED', 'NOT_CONFIGURED', 'PROVIDERS_FAILED', 'OUTPUT_REJECTED', "
                 "'CONSENT_WITHDRAWN'")


def upgrade() -> None:
    """Upgrade schema.

    Existing sessions get no consent, a stopped clock at 0 and no finish reason: nothing is guessed
    for them.
    """
    op.drop_constraint(op.f(CAPABILITY_CHECK), 'provider_calls', type_='check')
    op.create_check_constraint(op.f(CAPABILITY_CHECK), 'provider_calls',
                               f"capability IN ({NEW_CAPABILITIES})")

    op.add_column('interview_sessions', sa.Column('ai_consent', sa.Boolean(),
                                                  server_default=sa.text('false'), nullable=False))
    op.add_column('interview_sessions', sa.Column('active_seconds', sa.Double(),
                                                  server_default=sa.text('0'), nullable=False))
    op.add_column('interview_sessions', sa.Column('active_since', sa.DateTime(timezone=True),
                                                  nullable=True))
    op.add_column('interview_sessions', sa.Column('finish_reason', sa.String(length=20),
                                                  nullable=True))
    op.create_check_constraint(op.f('ck_interview_sessions_finish_reason'), 'interview_sessions',
                               "finish_reason IN ('PLAN_COMPLETED', 'TIME_LIMIT', 'CANDIDATE_ENDED')")
    op.create_check_constraint(op.f('ck_interview_sessions_active_seconds_not_negative'),
                               'interview_sessions', "active_seconds >= 0")
    op.create_check_constraint(
        op.f('ck_interview_sessions_finish_reason_only_when_finished'), 'interview_sessions',
        "finish_reason IS NULL OR status IN ('REPORT_GENERATION', 'COMPLETED')")

    op.create_table(
        'interview_consent_events',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True),
                  server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'],
                                name=op.f('fk_interview_consent_events_session_id_interview_sessions'),
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_interview_consent_events')),
    )
    op.create_index('ix_interview_consent_events_session_id_id', 'interview_consent_events',
                    ['session_id', 'id'])

    op.create_table(
        'interview_questions',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('session_id', sa.Uuid(), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('topic_position', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('followup_index', sa.SmallInteger(), nullable=False),
        sa.Column('rephrase_index', sa.SmallInteger(), nullable=False),
        sa.Column('text', sa.String(length=640), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('rules_reason', sa.String(length=20), nullable=True),
        sa.Column('anchor', sa.String(length=100), nullable=True),
        sa.Column('provider_call_id', sa.Uuid(), nullable=True),
        sa.Column('asked_at', sa.DateTime(timezone=True),
                  server_default=sa.text('clock_timestamp()'), nullable=False),
        sa.Column('clock_at_ask', sa.Double(), nullable=False),
        sa.Column('answer_kind', sa.String(length=20), nullable=True),
        sa.Column('answer_text', sa.Text(), nullable=True),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evaluation_status', sa.String(length=20), nullable=True),
        sa.CheckConstraint("kind IN ('TOPIC', 'FOLLOW_UP', 'REPHRASE')",
                           name=op.f('ck_interview_questions_kind')),
        sa.CheckConstraint("source IN ('AI', 'RULES')", name=op.f('ck_interview_questions_source')),
        sa.CheckConstraint(f"rules_reason IN ({RULES_REASONS})",
                           name=op.f('ck_interview_questions_rules_reason')),
        sa.CheckConstraint("answer_kind IN ('ANSWER', 'CLARIFY', 'DONT_KNOW', 'SKIP')",
                           name=op.f('ck_interview_questions_answer_kind')),
        sa.CheckConstraint("evaluation_status IN ('NOT_EVALUATED')",
                           name=op.f('ck_interview_questions_evaluation_status')),
        sa.CheckConstraint('seq >= 1', name=op.f('ck_interview_questions_seq_positive')),
        sa.CheckConstraint('topic_position >= 1',
                           name=op.f('ck_interview_questions_topic_position_positive')),
        sa.CheckConstraint('followup_index BETWEEN 0 AND 2',
                           name=op.f('ck_interview_questions_followup_index_range')),
        sa.CheckConstraint("kind <> 'TOPIC' OR followup_index = 0",
                           name=op.f('ck_interview_questions_topic_has_no_followup_index')),
        sa.CheckConstraint("kind <> 'FOLLOW_UP' OR followup_index >= 1",
                           name=op.f('ck_interview_questions_follow_up_has_followup_index')),
        sa.CheckConstraint('rephrase_index BETWEEN 0 AND 2',
                           name=op.f('ck_interview_questions_rephrase_index_range')),
        sa.CheckConstraint("(kind = 'REPHRASE') = (rephrase_index >= 1)",
                           name=op.f('ck_interview_questions_rephrase_index_matches_kind')),
        sa.CheckConstraint("btrim(text) <> ''", name=op.f('ck_interview_questions_text_not_blank')),
        sa.CheckConstraint("(source = 'AI') = (rules_reason IS NULL)",
                           name=op.f('ck_interview_questions_rules_reason_matches_source')),
        sa.CheckConstraint("(anchor IS NOT NULL) = (kind = 'FOLLOW_UP' AND source = 'AI')",
                           name=op.f('ck_interview_questions_anchor_only_on_ai_follow_ups')),
        sa.CheckConstraint('clock_at_ask >= 0',
                           name=op.f('ck_interview_questions_clock_at_ask_not_negative')),
        sa.CheckConstraint('char_length(answer_text) <= 10000',
                           name=op.f('ck_interview_questions_answer_text_length')),
        sa.CheckConstraint(
            "(answer_kind IS NULL) = (answered_at IS NULL) "
            "AND (answer_kind IS NULL) = (evaluation_status IS NULL)",
            name=op.f('ck_interview_questions_answer_fields_together')),
        sa.CheckConstraint('answer_text IS NULL OR answer_kind IS NOT NULL',
                           name=op.f('ck_interview_questions_answer_text_needs_kind')),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'],
                                name=op.f('fk_interview_questions_session_id_interview_sessions'),
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['provider_call_id'], ['provider_calls.id'],
                                name=op.f('fk_interview_questions_provider_call_id_provider_calls'),
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_interview_questions')),
        sa.UniqueConstraint('session_id', 'seq', name='uq_interview_questions_session_id_seq'),
    )
    op.create_index('uq_interview_questions_one_open_per_session', 'interview_questions',
                    ['session_id'], unique=True, postgresql_where=sa.text('answered_at IS NULL'))


def downgrade() -> None:
    """Downgrade schema.

    Refuses while any question, answer or consent change is stored: dropping the tables would
    silently delete them. Delete those sessions first (DELETE /api/interview-sessions/{id}) if you
    really want to go back. Question-generation call metadata (provider_calls rows with no prompt,
    output or candidate link) is deleted, since the older CHECK cannot hold it.
    """
    bind = op.get_bind()
    rows = {table: bind.scalar(sa.text(f"SELECT count(*) FROM {table}"))
            for table in ('interview_questions', 'interview_consent_events')}
    if any(rows.values()):
        raise RuntimeError(
            f"Refusing to downgrade: {rows['interview_questions']} interview question(s) and "
            f"{rows['interview_consent_events']} consent change(s) are stored, and this downgrade "
            "would delete them. Delete those sessions first, or stay on this revision.")
    op.drop_index('uq_interview_questions_one_open_per_session', table_name='interview_questions',
                  postgresql_where=sa.text('answered_at IS NULL'))
    op.drop_table('interview_questions')
    op.drop_index('ix_interview_consent_events_session_id_id',
                  table_name='interview_consent_events')
    op.drop_table('interview_consent_events')
    for name in ('finish_reason_only_when_finished', 'active_seconds_not_negative',
                 'finish_reason'):
        op.drop_constraint(op.f(f'ck_interview_sessions_{name}'), 'interview_sessions',
                           type_='check')
    for column in ('finish_reason', 'active_since', 'active_seconds', 'ai_consent'):
        op.drop_column('interview_sessions', column)
    op.execute("DELETE FROM provider_calls WHERE capability = 'QUESTION_GENERATION'")
    op.drop_constraint(op.f(CAPABILITY_CHECK), 'provider_calls', type_='check')
    op.create_check_constraint(op.f(CAPABILITY_CHECK), 'provider_calls',
                               f"capability IN ({OLD_CAPABILITIES})")
