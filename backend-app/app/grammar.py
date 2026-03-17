"""Hardcoded Polish grammar reference tables for endings practice."""

# ── Rzeczownik (Noun) endings ───────────────────────────────

NOUN_ENDINGS = {
    "mianownik": {
        "męski": {"singular": "-", "plural": "-i/-y/-owie/-e", "examples": "kot → koty, pan → panowie"},
        "żeński": {"singular": "-a/-i", "plural": "-y/-i/-e", "examples": "kobieta → kobiety, noc → noce"},
        "nijaki": {"singular": "-o/-e/-ę/-um", "plural": "-a/-e", "examples": "okno → okna, morze → morza"},
    },
    "dopełniacz": {
        "męski": {"singular": "-a/-u", "plural": "-ów/-y/-i", "examples": "kota, domu, studentów"},
        "żeński": {"singular": "-y/-i", "plural": "-∅/-y/-i", "examples": "kobiety, nocy, książek"},
        "nijaki": {"singular": "-a", "plural": "-∅/-y/-i", "examples": "okna, morza, okien"},
    },
    "celownik": {
        "męski": {"singular": "-owi/-u", "plural": "-om", "examples": "kotu, panu, kotom"},
        "żeński": {"singular": "-e/-i/-y", "plural": "-om", "examples": "kobiecie, nocy, kobietom"},
        "nijaki": {"singular": "-u", "plural": "-om", "examples": "oknu, morzu, oknom"},
    },
    "biernik": {
        "męski": {"singular": "żywotne: =dop., nieżywotne: =mian.", "plural": "żywotne: =dop., nieżywotne: =mian.", "examples": "kota (żyw.), dom (nieżyw.)"},
        "żeński": {"singular": "-ę/-∅", "plural": "-y/-i/-e", "examples": "kobietę, noc, kobiety"},
        "nijaki": {"singular": "= mianownik", "plural": "= mianownik", "examples": "okno, morze, okna"},
    },
    "narzędnik": {
        "męski": {"singular": "-em/-iem", "plural": "-ami/-mi", "examples": "kotem, panem, kotami"},
        "żeński": {"singular": "-ą/-ią", "plural": "-ami/-mi", "examples": "kobietą, nocą, kobietami"},
        "nijaki": {"singular": "-em/-iem", "plural": "-ami/-mi", "examples": "oknem, morzem, oknami"},
    },
    "miejscownik": {
        "męski": {"singular": "-e/-u/-ie", "plural": "-ach", "examples": "kocie, domu, kotach"},
        "żeński": {"singular": "-e/-i/-y", "plural": "-ach", "examples": "kobiecie, nocy, kobietach"},
        "nijaki": {"singular": "-e/-u/-ie", "plural": "-ach", "examples": "oknie, morzu, oknach"},
    },
    "wołacz": {
        "męski": {"singular": "-e/-u/-ie/-∅", "plural": "= mianownik", "examples": "kocie! panie! kotku!"},
        "żeński": {"singular": "-o/-u/-i/-y", "plural": "= mianownik", "examples": "kobieto! nocy!"},
        "nijaki": {"singular": "= mianownik", "plural": "= mianownik", "examples": "okno! morze!"},
    },
}

# ── Przymiotnik (Adjective) endings ─────────────────────────

ADJECTIVE_ENDINGS = {
    "mianownik": {
        "męski": {"singular": "-y/-i", "plural": "-e/-i/-y", "examples": "dobry, duży, dobrzy"},
        "żeński": {"singular": "-a", "plural": "-e", "examples": "dobra, duża, dobre"},
        "nijaki": {"singular": "-e", "plural": "-e", "examples": "dobre, duże, dobre"},
    },
    "dopełniacz": {
        "męski": {"singular": "-ego/-iego", "plural": "-ych/-ich", "examples": "dobrego, dobrych"},
        "żeński": {"singular": "-ej/-iej", "plural": "-ych/-ich", "examples": "dobrej, dobrych"},
        "nijaki": {"singular": "-ego/-iego", "plural": "-ych/-ich", "examples": "dobrego, dobrych"},
    },
    "celownik": {
        "męski": {"singular": "-emu/-iemu", "plural": "-ym/-im", "examples": "dobremu, dobrym"},
        "żeński": {"singular": "-ej/-iej", "plural": "-ym/-im", "examples": "dobrej, dobrym"},
        "nijaki": {"singular": "-emu/-iemu", "plural": "-ym/-im", "examples": "dobremu, dobrym"},
    },
    "biernik": {
        "męski": {"singular": "żywotne: =dop., nieżywotne: =mian.", "plural": "żywotne: =dop., nieżywotne: =mian.", "examples": "dobrego (żyw.), dobry (nieżyw.)"},
        "żeński": {"singular": "-ą/-ią", "plural": "-e", "examples": "dobrą, dobre"},
        "nijaki": {"singular": "= mianownik", "plural": "= mianownik", "examples": "dobre"},
    },
    "narzędnik": {
        "męski": {"singular": "-ym/-im", "plural": "-ymi/-imi", "examples": "dobrym, dobrymi"},
        "żeński": {"singular": "-ą/-ią", "plural": "-ymi/-imi", "examples": "dobrą, dobrymi"},
        "nijaki": {"singular": "-ym/-im", "plural": "-ymi/-imi", "examples": "dobrym, dobrymi"},
    },
    "miejscownik": {
        "męski": {"singular": "-ym/-im", "plural": "-ych/-ich", "examples": "dobrym, dobrych"},
        "żeński": {"singular": "-ej/-iej", "plural": "-ych/-ich", "examples": "dobrej, dobrych"},
        "nijaki": {"singular": "-ym/-im", "plural": "-ych/-ich", "examples": "dobrym, dobrych"},
    },
    "wołacz": {
        "męski": {"singular": "= mianownik", "plural": "= mianownik", "examples": "dobry!"},
        "żeński": {"singular": "= mianownik", "plural": "= mianownik", "examples": "dobra!"},
        "nijaki": {"singular": "= mianownik", "plural": "= mianownik", "examples": "dobre!"},
    },
}

# ── Czasownik (Verb) conjugation patterns ───────────────────

VERB_CONJUGATION_INFO = {
    "teraźniejszy": {
        "description": "Czas teraźniejszy (present tense)",
        "groups": [
            {
                "name": "I koniugacja (-ę, -esz)",
                "endings": {"ja": "-ę", "ty": "-esz", "on/ona/ono": "-e", "my": "-emy", "wy": "-ecie", "oni/one": "-ą"},
                "examples": "pisać → piszę, piszesz, pisze, piszemy, piszecie, piszą",
            },
            {
                "name": "II koniugacja (-ę, -isz/-ysz)",
                "endings": {"ja": "-ę", "ty": "-isz/-ysz", "on/ona/ono": "-i/-y", "my": "-imy/-ymy", "wy": "-icie/-ycie", "oni/one": "-ą"},
                "examples": "robić → robię, robisz, robi, robimy, robicie, robią",
            },
            {
                "name": "III koniugacja (-am, -asz)",
                "endings": {"ja": "-am", "ty": "-asz", "on/ona/ono": "-a", "my": "-amy", "wy": "-acie", "oni/one": "-ają"},
                "examples": "czytać → czytam, czytasz, czyta, czytamy, czytacie, czytają",
            },
            {
                "name": "IV koniugacja (-em, -esz)",
                "endings": {"ja": "-em", "ty": "-esz", "on/ona/ono": "-e", "my": "-emy", "wy": "-ecie", "oni/one": "-eją/-edzą"},
                "examples": "umieć → umiem, umiesz, umie, umiemy, umiecie, umieją",
            },
        ],
    },
    "przeszły": {
        "description": "Czas przeszły (past tense)",
        "info": "Odmiana zależy od rodzaju (gender) podmiotu.",
        "endings_by_gender": {
            "męski": {"ja": "-łem", "ty": "-łeś", "on": "-ł", "my": "-liśmy", "wy": "-liście", "oni": "-li"},
            "żeński": {"ja": "-łam", "ty": "-łaś", "ona": "-ła", "my": "-łyśmy", "wy": "-łyście", "one": "-ły"},
            "nijaki": {"ono": "-ło"},
        },
        "examples": "robić → robiłem/robiłam, robiłeś/robiłaś, robił/robiła/robiło, robiliśmy/robiłyśmy",
    },
    "przyszły": {
        "description": "Czas przyszły (future tense)",
        "info": "Złożony: będę + bezokolicznik lub będę + imiesłów (forma -ł). Prosty: przedrostek + czas teraźniejszy (dokonane).",
        "compound_pattern": "będę + infinitive / będę + past participle",
        "examples": "będę robić / będę robił(a), zrobię (dokonany)",
    },
}


# ── Common exceptions & notes ────────────────────────────────

GRAMMAR_NOTES = {
    "biernik_rzeczownik": (
        "Biernik (Accusative) — kluczowe zasady:\n"
        "• Męski żywotny (animate): biernik = dopełniacz (widzę kota)\n"
        "• Męski nieżywotny (inanimate): biernik = mianownik (widzę dom)\n"
        "• Żeński -a → -ę (kobieta → kobietę)\n"
        "• Żeński spółgłoskowy: = mianownik (noc → noc)\n"
        "• Nijaki: = mianownik (okno → okno)"
    ),
    "dopelniacz_rzeczownik": (
        "Dopełniacz (Genitive) — kluczowe zasady:\n"
        "• Męski: -a (żywotne i wiele nieżywotnych) lub -u (materiały, abstrakcje, zapożyczenia)\n"
        "• Żeński: -y (po twardej) lub -i (po miękkiej/k/g)\n"
        "• Nijaki: -a\n"
        "• Używany po: nie ma, bez, do, od, z (from), obok, dla"
    ),
    "celownik_rzeczownik": (
        "Celownik (Dative) — kluczowe zasady:\n"
        "• Męski: -owi (najczęściej), -u (pan → panu, chłopiec → chłopcu)\n"
        "• Żeński: -e (z alternacją: kobieta → kobiecie, k→c, g→dz), -i/-y\n"
        "• Nijaki: -u\n"
        "• Używany po: dawać komuś, pomagać komuś, podobać się komuś"
    ),
    "narzednik_rzeczownik": (
        "Narzędnik (Instrumental) — kluczowe zasady:\n"
        "• Męski: -em (kot → kotem)\n"
        "• Żeński: -ą (kobieta → kobietą)\n"
        "• Nijaki: -em (okno → oknem)\n"
        "• Używany po: z (with), być + narzędnik, nad, pod, przed, między"
    ),
    "miejscownik_rzeczownik": (
        "Miejscownik (Locative) — kluczowe zasady:\n"
        "• Męski: -e (z alternacją: kot → kocie, d→dzie, t→cie) lub -u\n"
        "• Żeński: -e (z alternacją) lub -i/-y\n"
        "• Nijaki: -e lub -u\n"
        "• Używany po: w, na, o, po, przy"
    ),
    "wolacz_rzeczownik": (
        "Wołacz (Vocative) — kluczowe zasady:\n"
        "• Męski: -e (z alternacją) lub -u (częsty w potocznym)\n"
        "• Żeński -a → -o (kobieta → kobieto!), -i → -i\n"
        "• Nijaki: = mianownik\n"
        "• Zdrobnienia: -u (kotku!, tatku!)"
    ),
    "verb_present": (
        "Czas teraźniejszy — kluczowe zasady:\n"
        "• 4 grupy koniugacji wg końcówek: -ę/-esz, -ę/-isz, -am/-asz, -em/-esz\n"
        "• Alternacje spółgłosek: pisać→piszę, prosić→proszę\n"
        "• Najczęstsze nieregularne: być (jestem), jeść (jem), iść (idę)"
    ),
    "verb_past": (
        "Czas przeszły — kluczowe zasady:\n"
        "• Temat przeszły + końcówka rodzajowa + końcówka osobowa\n"
        "• Rodzaj podmiotu zmienia formę: robiłem (m.) / robiłam (f.)\n"
        "• 3 os. nie ma końcówki osobowej: robił / robiła / robiło\n"
        "• Nieregularne: iść → szedł/szła, jeść → jadł/jadła"
    ),
    "verb_future": (
        "Czas przyszły — kluczowe zasady:\n"
        "• Niedokonane: będę + bezokolicznik (będę robić) lub będę + forma -ł (będę robił/a)\n"
        "• Dokonane: przedrostek + odmiana teraźniejsza (zrobię, napiszę)\n"
        "• być: będę, będziesz, będzie, będziemy, będziecie, będą"
    ),
}


def get_grammar_reference(part_of_speech: str, case: str = None, tense: str = None) -> dict:
    """Get the relevant grammar reference for a practice question."""
    result = {}

    if part_of_speech == "rzeczownik":
        if case:
            result["endings"] = NOUN_ENDINGS.get(case, {})
            note_key = f"{case}_rzeczownik"
            if note_key in GRAMMAR_NOTES:
                result["notes"] = GRAMMAR_NOTES[note_key]
        else:
            result["endings"] = NOUN_ENDINGS
    elif part_of_speech == "przymiotnik":
        if case:
            result["endings"] = ADJECTIVE_ENDINGS.get(case, {})
            # Reuse noun case notes where relevant
            note_key = f"{case}_rzeczownik"
            if note_key in GRAMMAR_NOTES:
                result["notes"] = GRAMMAR_NOTES[note_key]
        else:
            result["endings"] = ADJECTIVE_ENDINGS
    elif part_of_speech == "czasownik":
        if tense:
            result["conjugation_info"] = VERB_CONJUGATION_INFO.get(tense, {})
            tense_map = {
                "teraźniejszy": "verb_present",
                "przeszły": "verb_past",
                "przyszły": "verb_future",
            }
            note_key = tense_map.get(tense)
            if note_key and note_key in GRAMMAR_NOTES:
                result["notes"] = GRAMMAR_NOTES[note_key]
        else:
            result["conjugation_info"] = VERB_CONJUGATION_INFO

    return result
