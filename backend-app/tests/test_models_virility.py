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


from app.models import Pronoun


def test_pronoun_splits_oni_one():
    values = {p.value for p in Pronoun}
    assert "oni" in values
    assert "one" in values
    assert "oni/one" not in values


from app.models import Aspect, Word


def test_aspect_enum_values():
    assert {a.value for a in Aspect} == {"dokonany", "niedokonany"}


def test_word_accepts_optional_aspect():
    w = Word(polish="zrobić", english="to do", ukrainian="зробити",
             part_of_speech="czasownik", aspect=Aspect.dokonany)
    assert w.aspect == Aspect.dokonany
    w2 = Word(polish="kot", english="cat", ukrainian="кіт", part_of_speech="rzeczownik")
    assert w2.aspect is None
