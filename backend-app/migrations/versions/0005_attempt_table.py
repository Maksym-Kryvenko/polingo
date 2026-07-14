"""create unified attempt table

Revision ID: 0005_attempt_table
Revises: 0004_word_aspect
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_attempt_table"
down_revision = "0004_word_aspect"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attempt",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("word_id", sa.Integer(), sa.ForeignKey("word.id"), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("language_set", sa.String(), nullable=True),
        sa.Column("direction", sa.String(), nullable=True),
        sa.Column("part_of_speech", sa.String(), nullable=True),
        sa.Column("was_correct", sa.Boolean(), nullable=False),
        sa.Column("user_answer", sa.String(), nullable=True),
        sa.Column("correct_answer", sa.String(), nullable=True),
        sa.Column("practice_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_attempt_word_id", "attempt", ["word_id"])
    op.create_index("ix_attempt_kind", "attempt", ["kind"])
    op.create_index("ix_attempt_practice_date", "attempt", ["practice_date"])


def downgrade() -> None:
    op.drop_index("ix_attempt_practice_date", table_name="attempt")
    op.drop_index("ix_attempt_kind", table_name="attempt")
    op.drop_index("ix_attempt_word_id", table_name="attempt")
    op.drop_table("attempt")
