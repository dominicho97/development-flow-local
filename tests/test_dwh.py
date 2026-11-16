from unittest.mock import MagicMock

import pandas as pd
import pytest

from dags.datawarehouse import data_modification, dwh


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
