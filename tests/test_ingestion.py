import pandas as pd
import pytest

from src.ingestion import load_products


def test_load_valid_csv(tmp_path):
    file = tmp_path / "products.csv"
    file.write_text(
        'record_id,sku,product_name,listed_price\nR-1,SYN-1,Rice,"€12,99"\n',
        encoding="utf-8",
    )

    df = load_products(file)

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df.loc[0, "listed_price"] == "€12,99"


def test_missing_file(tmp_path):
    file = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        load_products(file)


def test_missing_columns(tmp_path):
    file = tmp_path / "products.csv"
    file.write_text(
        "product_name,listed_price\nRice,12.99\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        load_products(file)


def test_malformed_csv(tmp_path):
    file = tmp_path / "products.csv"
    file.write_text(
        "record_id,sku,product_name,listed_price\n"
        "R-1,SYN-1,Rice,5.00\n"
        "R-2,SYN-2,Tea,3.00,extra\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid CSV"):
        load_products(file)
