"""remap masculine gender to the 5-gender model

Revision ID: 0002_gender_five_way
Revises: 0001_baseline
"""
from alembic import op

revision = "0002_gender_five_way"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Legacy "męski" carried no animacy; default to inanimate (most common).
    op.execute("UPDATE worddeclension SET gender = 'męskorzeczowy' WHERE gender = 'męski'")
    op.execute("UPDATE word SET gender = 'męskorzeczowy' WHERE gender = 'męski'")


def downgrade() -> None:
    op.execute(
        "UPDATE worddeclension SET gender = 'męski' "
        "WHERE gender IN ('męskoosobowy', 'męskozywotny', 'męskorzeczowy')"
    )
    op.execute(
        "UPDATE word SET gender = 'męski' "
        "WHERE gender IN ('męskoosobowy', 'męskozywotny', 'męskorzeczowy')"
    )
