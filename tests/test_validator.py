import pandas as pd
import pytest

from sales_merger.columns import FILE_COL, REQUIRED, ROW_COL
from sales_merger.errors import *
from sales_merger.validator import MissingColumnsError, select_columns, validate_rows
from tests.helpers import GOOD, make_frame


def test_select_columns_maps_and_numbers_rows():
    raw = pd.DataFrame({"order_id": ["1", "2"], "DATE": ["x", "y"], "Товар": ["a", "b"], "Категория": ["c", "d"],
                        "Кол-во": ["1", "1"], "Цена": ["1", "1"], "Сотрудник": ["A", "B"], "Лишнее": ["", ""]})
    df = select_columns(raw, "a.csv")
    assert list(df.columns) == REQUIRED + [FILE_COL, ROW_COL]
    assert df[ROW_COL].tolist() == [2, 3] and df[FILE_COL].tolist() == ["a.csv"] * 2


def test_select_columns_missing():
    with pytest.raises(MissingColumnsError) as e:
        select_columns(pd.DataFrame({"Дата": [], "Цена": []}), "a.csv")
    assert e.value.missing[:2] == ["Номер заказа", "Товар"]


def test_validate_rows_keeps_good_and_collects_all_errors():
    rows = [dict(GOOD),
            {**GOOD, "Номер заказа": "1002", "Цена": ""},
            {**GOOD, "Номер заказа": "1003", "Цена": "-1"},
            {**GOOD, "Номер заказа": "1004", "Количество": "0", "Дата": "bad"},
            {**GOOD, "Номер заказа": "1005"}]
    errs = ErrorCollector()
    out = validate_rows(make_frame(rows), errs)
    assert out["Номер заказа"].tolist() == ["1001", "1005"]
    assert str(out["Дата"].dtype).startswith("datetime64") and out["Количество"].dtype == "int64" and out["Цена"].dtype == "float64"
    df = errs.to_dataframe()
    assert len(df) == 4 and set(df["Тип ошибки"]) == {EMPTY_FIELD, BAD_VALUE, BAD_FORMAT}
    assert df[df["Номер заказа"] == "1004"]["Строка"].tolist() == [5, 5]
    assert "Цена" in df.iloc[0]["Описание"] and df.iloc[2]["Исходное значение"] in ("0", "bad")


def test_validate_rows_all_rejected_returns_typed_empty_frame():
    out = validate_rows(make_frame([{**GOOD, "Цена": ""}]), ErrorCollector())
    assert out.empty and list(out.columns) == REQUIRED + [FILE_COL, ROW_COL]


def test_validate_rows_out_of_range_values_become_errors_not_crash():
    rows = [dict(GOOD),
            {**GOOD, "Номер заказа": "2001", "Дата": "01.01.3000"},
            {**GOOD, "Номер заказа": "2002", "Количество": "99999999999999999999"},
            {**GOOD, "Номер заказа": "2003", "Цена": "9" * 400}]
    errs = ErrorCollector()
    out = validate_rows(make_frame(rows), errs)
    assert out["Номер заказа"].tolist() == ["1001"] and errs.counts_by_type() == {BAD_VALUE: 3}
