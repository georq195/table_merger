"""Выручка, показатели и группировки для отчёта."""
from __future__ import annotations

import pandas as pd

from sales_merger.models import Metrics

REVENUE = "Выручка"


def add_revenue(df: pd.DataFrame) -> pd.DataFrame:
    """Добавляет «Выручка» = round(Количество * Цена, 2)."""
    out = df.copy()
    out[REVENUE] = (out["Количество"] * out["Цена"]).round(2)
    return out


def _avg(revenue: float, orders: int) -> float:
    return round(revenue / orders, 2) if orders else 0.0


def compute_metrics(df: pd.DataFrame) -> Metrics:
    """`df` непустой, со столбцом «Выручка»."""
    total = round(float(df[REVENUE].sum()), 2)
    orders = len(df)

    grouped = df.groupby("Менеджер", sort=False)[REVENUE].agg(["size", "sum"]).reset_index()
    by_manager = pd.DataFrame({
        "Менеджер": grouped["Менеджер"],
        "Заказы": grouped["size"].astype("int64"),
        "Выручка": grouped["sum"].round(2),
    })
    by_manager["Средний чек"] = [_avg(r, n) for r, n in zip(by_manager["Выручка"], by_manager["Заказы"])]
    by_manager["Доля выручки, %"] = (by_manager["Выручка"] / total * 100).round(2) if total else 0.0
    by_manager = (by_manager.sort_values(["Выручка", "Менеджер"], ascending=[False, True], kind="stable")
                  .reset_index(drop=True))

    months = df["Дата"].dt.to_period("M")
    per_month = df.groupby(months)[REVENUE].agg(["size", "sum"])
    full = pd.period_range(months.min(), months.max(), freq="M")
    per_month = per_month.reindex(full, fill_value=0)
    by_month = pd.DataFrame({
        "Месяц": [str(p) for p in full],
        "Заказы": per_month["size"].astype("int64").to_numpy(),
        "Выручка": per_month["sum"].astype("float64").round(2).to_numpy(),
    })
    by_month["Средний чек"] = [_avg(r, n) for r, n in zip(by_month["Выручка"], by_month["Заказы"])]

    return Metrics(
        total_revenue=total,
        orders=orders,
        avg_check=_avg(total, orders),
        by_manager=by_manager,
        by_month=by_month,
        period_start=df["Дата"].min().date(),
        period_end=df["Дата"].max().date(),
    )
