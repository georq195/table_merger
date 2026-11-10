from sales_merger.metrics import add_revenue, compute_metrics
from tests.helpers import make_typed_frame


def test_metrics_known_dataset():
    m = compute_metrics(add_revenue(make_typed_frame()))
    assert (m.total_revenue, m.orders, m.avg_check) == (9500.0, 3, 3166.67)
    assert m.by_manager.iloc[0].tolist() == ["Alex", 2, 8500.0, 4250.0, 89.47]
    assert m.by_manager.iloc[1].tolist() == ["Maria", 1, 1000.0, 1000.0, 10.53]
    assert m.by_month.values.tolist() == [["2026-10", 2, 8000.0, 4000.0], ["2026-11", 0, 0.0, 0.0], ["2026-12", 1, 1500.0, 1500.0]]
    assert (str(m.period_start), str(m.period_end)) == ("2026-10-15", "2026-12-01")


def test_metrics_columns():
    m = compute_metrics(add_revenue(make_typed_frame()))
    assert list(m.by_manager.columns) == ["Менеджер", "Заказы", "Выручка", "Средний чек", "Доля выручки, %"]
    assert list(m.by_month.columns) == ["Месяц", "Заказы", "Выручка", "Средний чек"]


def test_add_revenue_rounds():
    df = add_revenue(make_typed_frame(price=0.1, qty=3))
    assert df["Выручка"].iloc[0] == 0.3
