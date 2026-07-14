"""copy practice/endings records into attempt, drop old tables

Revision ID: 0006_attempt_data_and_drop
Revises: 0005_attempt_table
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_attempt_data_and_drop"
down_revision = "0005_attempt_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO attempt (word_id, kind, language_set, direction, part_of_speech,
                             was_correct, user_answer, correct_answer, practice_date, created_at)
        SELECT word_id, 'practice', language_set, direction, NULL,
               was_correct, user_answer, correct_answer, practice_date, created_at
        FROM practicerecord
    """)
    op.execute("""
        INSERT INTO attempt (word_id, kind, language_set, direction, part_of_speech,
                             was_correct, user_answer, correct_answer, practice_date, created_at)
        SELECT word_id, 'endings', NULL, NULL, part_of_speech,
               was_correct, user_answer, correct_answer, practice_date, created_at
        FROM endingspracticerecord
    """)
    op.drop_table("practicerecord")
    op.drop_table("endingspracticerecord")


def downgrade() -> None:
    op.create_table(
        "practicerecord",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("word.id"), nullable=False),
        sa.Column("language_set", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("user_answer", sa.String(), nullable=True),
        sa.Column("correct_answer", sa.String(), nullable=True),
        sa.Column("practice_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "endingspracticerecord",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("word.id"), nullable=False),
        sa.Column("part_of_speech", sa.String(), nullable=False),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("user_answer", sa.String(), nullable=True),
        sa.Column("correct_answer", sa.String(), nullable=True),
        sa.Column("practice_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.execute("""
        INSERT INTO practicerecord (word_id, language_set, direction, was_correct,
                                    user_answer, correct_answer, practice_date, created_at)
        SELECT word_id, language_set, direction, was_correct,
               user_answer, correct_answer, practice_date, created_at
        FROM attempt WHERE kind = 'practice'
    """)
    op.execute("""
        INSERT INTO endingspracticerecord (word_id, part_of_speech, was_correct,
                                           user_answer, correct_answer, practice_date, created_at)
        SELECT word_id, part_of_speech, was_correct,
               user_answer, correct_answer, practice_date, created_at
        FROM attempt WHERE kind = 'endings'
    """)
    op.execute("DELETE FROM attempt")
