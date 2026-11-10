import datetime as dt, pytest
from sales_merger.validator import parse_date, parse_price, parse_quantity, ParseError
from sales_merger.errors import BAD_FORMAT, BAD_VALUE

@pytest.mark.parametrize("text,expected", [
    ("2026-10-15", dt.date(2026,10,15)), ("15.10.2026", dt.date(2026,10,15)),
    ("15/10/2026", dt.date(2026,10,15)), ("03/04/2026", dt.date(2026,4,3)),
    ("2026-10-15 00:00:00", dt.date(2026,10,15))])
def test_parse_date_ok(text, expected):
    assert parse_date(text) == expected

@pytest.mark.parametrize("text", ["31.02.2026", "abc", "2026/10/15", "15-10-26"])
def test_parse_date_bad(text):
    with pytest.raises(ParseError) as e: parse_date(text)
    assert e.value.kind == BAD_FORMAT

@pytest.mark.parametrize("text", ["3500.00", "3500,00", "3 500,00", "3 500,00", "3 500,00", "3500"])
def test_parse_price_ok(text):
    assert parse_price(text) == 3500.0

def test_price_zero_allowed():
    assert parse_price("0") == 0.0

def test_price_negative_is_value_error():
    with pytest.raises(ParseError) as e: parse_price("-5")
    assert e.value.kind == BAD_VALUE

@pytest.mark.parametrize("text", ["abc", "3500 ₽", "1.234,56", "1e3"])
def test_price_bad_format(text):
    with pytest.raises(ParseError) as e: parse_price(text)
    assert e.value.kind == BAD_FORMAT

@pytest.mark.parametrize("text,expected", [("2", 2), ("2.0", 2), ("2,0", 2)])
def test_quantity_ok(text, expected):
    assert parse_quantity(text) == expected

@pytest.mark.parametrize("text,kind", [("2.5", BAD_FORMAT), ("abc", BAD_FORMAT), ("0", BAD_VALUE), ("-1", BAD_VALUE)])
def test_quantity_bad(text, kind):
    with pytest.raises(ParseError) as e: parse_quantity(text)
    assert e.value.kind == kind


# значения вне допустимого диапазона не должны ронять запуск
@pytest.mark.parametrize("text", ["01.01.1000", "01.01.3000", "9999-12-31", "2026-10-15 00:00:00".replace("2026", "1800")])
def test_parse_date_out_of_range_is_bad_value(text):
    with pytest.raises(ParseError) as e: parse_date(text)
    assert e.value.kind == BAD_VALUE

def test_parse_quantity_huge_is_bad_value():
    with pytest.raises(ParseError) as e: parse_quantity("99999999999999999999")
    assert e.value.kind == BAD_VALUE

def test_parse_price_infinite_is_bad_value():
    with pytest.raises(ParseError) as e: parse_price("9" * 400)
    assert e.value.kind == BAD_VALUE
