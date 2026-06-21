from app.models import GrammaticalGender, is_animate_masculine, is_virile


def test_gender_has_five_members():
    assert {g.value for g in GrammaticalGender} == {
        "męskoosobowy", "męskozywotny", "męskorzeczowy", "żeński", "nijaki",
    }


def test_is_virile_only_true_for_meskoosobowy():
    assert is_virile(GrammaticalGender.meskoosobowy) is True
    assert is_virile("męskoosobowy") is True
    assert is_virile(GrammaticalGender.meskozywotny) is False
    assert is_virile(GrammaticalGender.zenski) is False
    assert is_virile(None) is False


def test_is_animate_masculine_covers_both_masc_animate_genders():
    assert is_animate_masculine(GrammaticalGender.meskoosobowy) is True
    assert is_animate_masculine(GrammaticalGender.meskozywotny) is True
    assert is_animate_masculine(GrammaticalGender.meskorzeczowy) is False
    assert is_animate_masculine(GrammaticalGender.zenski) is False
    assert is_animate_masculine(None) is False
