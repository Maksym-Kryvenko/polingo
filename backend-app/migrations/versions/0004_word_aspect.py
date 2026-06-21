"""add nullable aspect column to word

Revision ID: 0004_word_aspect
Revises: 0003_pronoun_virility
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_word_aspect"
down_revision = "0003_pronoun_virility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("word") as batch:
        batch.add_column(sa.Column("aspect", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("word") as batch:
        batch.drop_column("aspect")
