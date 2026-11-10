import pytest
from sales_merger.columns import REQUIRED, SYNONYMS, normalize_header, map_columns

def test_normalize_header():
    assert normalize_header("  Кол-во ") == "кол-во"
    assert normalize_header("Дата   Заказа") == "дата заказа"
    assert normalize_header("Её") == "ее"

@pytest.mark.parametrize("field,name", [(f, n) for f, names in SYNONYMS.items() for n in names])
def test_every_synonym_maps(field, name):
    mapping, missing = map_columns([name])
    assert mapping == {name: field}

def test_synonym_table_matches_spec():
    assert SYNONYMS["Номер заказа"] == ["Номер заказа", "№ заказа", "ID заказа", "order_id"]
    assert SYNONYMS["Менеджер"] == ["Менеджер", "Сотрудник", "manager"]
    assert list(SYNONYMS) == REQUIRED

def test_mixed_headers_and_extra_column():
    cols = ["Order_ID ", "DATE", "Товар", "Категория", "Кол-во", "Цена", "сотрудник", "Комментарий"]
    mapping, missing = map_columns(cols)
    assert missing == [] and "Комментарий" not in mapping
    assert mapping["сотрудник"] == "Менеджер"

def test_missing_reported_in_required_order():
    _, missing = map_columns(["Дата", "Цена"])
    assert missing == ["Номер заказа", "Товар", "Категория", "Количество", "Менеджер"]
