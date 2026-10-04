from sumcore.charset import ASC, asc_character

def test_codes():
    assert len(ASC) >= 3135
    assert asc_character(219) == "█"
    assert asc_character(65) == "A"
