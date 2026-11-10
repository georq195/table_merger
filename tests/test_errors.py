from sales_merger.errors import *

def test_add_and_dataframe():
    e = ErrorCollector()
    e.add("a.csv", 3, "1001", EMPTY_FIELD, "Поле «Цена» не заполнено")
    e.add("b.csv", None, "", NO_COLUMNS, "Нет столбцов: Цена")
    df = e.to_dataframe()
    assert list(df.columns) == ERROR_COLUMNS and len(e) == 2
    assert df.iloc[0]["Строка"] == 3 and df.iloc[1]["Строка"] == ""

def test_counts_by_type_sorted_desc():
    e = ErrorCollector()
    for _ in range(2): e.add("a", 2, "1", BAD_FORMAT, "x")
    for _ in range(3): e.add("a", 2, "1", EMPTY_FIELD, "x")
    assert list(e.counts_by_type().items()) == [(EMPTY_FIELD, 3), (BAD_FORMAT, 2)]

def test_empty_collector():
    df = ErrorCollector().to_dataframe()
    assert df.empty and list(df.columns) == ERROR_COLUMNS
