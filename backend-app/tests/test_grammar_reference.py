from app.grammar import NOUN_ENDINGS, ADJECTIVE_ENDINGS, get_grammar_reference


def test_noun_accusative_masc_plural_uses_virility_not_animacy():
    plural = NOUN_ENDINGS["biernik"]["męski"]["plural"]
    # The wrong (singular) animacy wording must be gone...
    assert "żywotne" not in plural
    # ...and the correct virility split must be present.
    assert "męskoosobowy" in plural
    assert "niemęskoosobowy" in plural


def test_adjective_accusative_masc_plural_uses_virility():
    plural = ADJECTIVE_ENDINGS["biernik"]["męski"]["plural"]
    assert "żywotne" not in plural
    assert "męskoosobowy" in plural


def test_noun_nominative_masc_plural_labels_virility():
    plural = NOUN_ENDINGS["mianownik"]["męski"]["plural"]
    assert "męskoosobowy" in plural


def test_get_grammar_reference_still_returns_biernik_noun_notes():
    ref = get_grammar_reference("rzeczownik", case="biernik")
    assert "endings" in ref and "notes" in ref
