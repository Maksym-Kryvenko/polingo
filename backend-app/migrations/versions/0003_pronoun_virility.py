"""relabel oni/one conjugations to the virile oni form

Revision ID: 0003_pronoun_virility
Revises: 0002_gender_five_way
"""
from alembic import op

revision = "0003_pronoun_virility"
down_revision = "0002_gender_five_way"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing "oni/one" forms map to the virile "oni".
    op.execute("UPDATE verbconjugation SET pronoun = 'oni' WHERE pronoun = 'oni/one'")
    # Present/future are identical for oni/one, so duplicate those rows as "one"
    # to avoid an empty result on pronoun='one' queries. Past tense differs
    # (robili vs robiły) and is left for form-gen to regenerate — not fabricated.
    op.execute(
        "INSERT INTO verbconjugation (word_id, pronoun, tense, conjugated_form) "
        "SELECT word_id, 'one', tense, conjugated_form FROM verbconjugation "
        "WHERE pronoun = 'oni' AND tense IN ('teraźniejszy', 'przyszły')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM verbconjugation WHERE pronoun = 'one'")
    op.execute("UPDATE verbconjugation SET pronoun = 'oni/one' WHERE pronoun = 'oni'")
