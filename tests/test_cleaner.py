import pandas as pd

from sales_merger.cleaner import *
from sales_merger.errors import DUPLICATE, ErrorCollector
from tests.helpers import GOOD, make_frame


def test_clean_text():
    df = clean_text(make_frame([{**GOOD, "Менеджер": "  Alex   Smith ", "Товар": " Keyboard "}]))
    assert df.iloc[0]["Менеджер"] == "Alex Smith" and df.iloc[0]["Товар"] == "Keyboard"


def test_clean_text_strips_nbsp():
    df = clean_text(make_frame([{**GOOD, "Менеджер": " Alex "}]))
    assert df.iloc[0]["Менеджер"] == "Alex"


def test_drop_empty_rows_counts_and_keeps_partial():
    df, n = drop_empty_rows(clean_text(make_frame([dict(GOOD), {}, {"Товар": "   "}, {"Цена": "5"}])))
    assert n == 2 and len(df) == 2


def test_drop_duplicates_keeps_first_and_reports_kept_source():
    a = make_frame([dict(GOOD), {**GOOD, "Номер заказа": "1002"}], "a.csv")
    b = make_frame([{}, {}, {}, dict(GOOD)], "b.csv").iloc[3:]   # строка 5 файла b.csv
    errs = ErrorCollector()
    out = drop_duplicates(pd.concat([a, b], ignore_index=True), errs)
    assert out["Номер заказа"].tolist() == ["1001", "1002"]
    row = errs.to_dataframe().iloc[0]
    assert row["Тип ошибки"] == DUPLICATE and row["Файл"] == "b.csv" and row["Строка"] == 5
    assert "a.csv" in row["Описание"] and "2" in row["Описание"]


def test_unify_managers_first_spelling_wins():
    df = unify_managers(make_frame([{"Менеджер": m} for m in ["Alex", "alex", "ALEX", "Maria"]]))
    assert df["Менеджер"].tolist() == ["Alex", "Alex", "Alex", "Maria"]
