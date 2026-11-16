from unittest.mock import MagicMock

import pandas as pd
import pytest

from dags.datawarehouse import data_modification, dwh
from dags.datawarehouse.data_transformation import transform_data


def test_core_transformation_excludes_missing_skus(caplog):
    data = pd.DataFrame(
        {
            "sku": ["A", "A", "", "  ", None],
            "last_seen": ["2026-01-01", "2026-02-01", "", "", ""],
            "product_name": ["Old", "Latest", "Missing", "Blank", "Null"],
        }
    )
    result = transform_data(data)
    assert result["sku"].tolist() == ["A"]
    assert result["product_name"].tolist() == ["Latest"]
    assert "Skipping 3 products without a SKU" in caplog.text
    assert len(data) == 5


def test_staging_keeps_repeated_source_ids_and_retry_keys(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(data_modification, "get_db_connection", lambda: conn)
    row = {
        "record_id": "R-1",
        "sku": "A",
        "product_name": "Rice",
        "category": "Food",
        "listed_price": "EUR 2",
        "stock_qty": "5",
    }
    data = pd.DataFrame([row, row])
    assert data_modification.populate_table(data, "staging") == 2
    cursor = conn.cursor.return_value.__enter__.return_value
    inserts = [
        call.args[1]
        for call in cursor.execute.call_args_list
        if "INSERT INTO" in call.args[0]
    ]
    assert inserts[0][0] == '["R-1", 1]'
    assert inserts[1][0] == '["R-1", 2]'
    cursor.reset_mock()
    data_modification.populate_table(data, "staging")
    retried = [
        call.args[1]
        for call in cursor.execute.call_args_list
        if "INSERT INTO" in call.args[0]
    ]
    assert retried == inserts
    assert "source_record_id" not in data.columns


def test_staging_and_core_use_distinct_data(monkeypatch):
    raw = pd.DataFrame({"sku": ["A", "A"]})
    cleaned = pd.DataFrame({"sku": ["A"]})
    monkeypatch.setattr(dwh, "load_data", lambda config: raw)
    transform = MagicMock(return_value=cleaned)
    populate = MagicMock(side_effect=[2, 1])
    monkeypatch.setattr(dwh, "transform_data", transform)
    monkeypatch.setattr(dwh, "populate_table", populate)
    assert dwh.staging_table() == 2
    assert dwh.core_table() == 1
    assert populate.call_args_list[0].args[0] is raw
    assert populate.call_args_list[0].args[1] == "staging"
    assert populate.call_args_list[1].args[0] is cleaned
    assert populate.call_args_list[1].args[1] == "core"


def test_upsert_nulls_and_failure_cleanup(monkeypatch):
    conn = MagicMock()
    monkeypatch.setattr(data_modification, "get_db_connection", lambda: conn)
    data = pd.DataFrame(
        [
            {
                "sku": "A",
                "product_name": "Rice",
                "category": None,
                "listed_price": float("nan"),
                "stock_qty": pd.NA,
            }
        ]
    )
    assert data_modification.populate_table(data, "core") == 1
    cursor = conn.cursor.return_value.__enter__.return_value
    query, values = cursor.execute.call_args.args
    assert "ON CONFLICT (sku)" in query
    assert values == ("A", "Rice", None, None, None)
    cursor.execute.side_effect = RuntimeError("failed")
    with pytest.raises(RuntimeError, match="failed"):
        data_modification.populate_table(data, "core")
    assert conn.__exit__.call_args.args[0] is RuntimeError
    assert conn.close.call_count == 2
