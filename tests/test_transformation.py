import pandas as pd
import pytest

from src.transformation import (
    clean_active,
    clean_category,
    clean_country,
    clean_currency,
    clean_date,
    clean_price,
    clean_products,
    clean_stock,
    deduplicate_products,
)


def test_clean_products_removes_whitespace():
    raw = pd.DataFrame(
        {
            "sku": [" SYN-0001 "],
            "product_name": [" Jasmine Rice "],
            "category": [" rice & noodles "],
        }
    )

    cleaned = clean_products(raw)

    assert cleaned.loc[0, "sku"] == "SYN-0001"
    assert cleaned.loc[0, "product_name"] == "Jasmine Rice"
    assert cleaned.loc[0, "category"] == "Rice & Noodles"


# pytest decoratator to run the test with multiple inputs and expected outputs
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("€12,99", 12.99, id="euro-decimal-comma"),
        pytest.param("EUR 3.29", 3.29, id="currency-prefix"),
        pytest.param("2.09 EUR", 2.09, id="currency-suffix"),
        pytest.param("€ 2.99", 2.99, id="currency-symbol-with-space"),
        pytest.param("14,99 €", 14.99, id="currency-suffix-with-space"),
        pytest.param("5.49", 5.49, id="decimal-dot"),
        pytest.param("1,69", 1.69, id="decimal-comma"),
        pytest.param(" 2.19 ", 2.19, id="whitespace"),
        pytest.param("", None, id="empty"),
        pytest.param("N/A", None, id="missing-value"),
        pytest.param("invalid", None, id="invalid-text"),
    ],
)
def test_clean_price(raw, expected):
    assert clean_price(raw) == expected


# test if the clean_products function uses clean_price to normalize the listed_price column
def test_clean_products_normalizes_prices():
    raw = pd.DataFrame(
        {
            "sku": ["SYN-0001", "SYN-0002", "SYN-0003"],
            "category": ["Rice & Noodles", "Beverages", "Rice & Noodles"],
            "listed_price": ["€12,99", "5.49", "N/A"],
        }
    )

    cleaned = clean_products(raw)

    assert cleaned.loc[0, "listed_price"] == 12.99
    assert cleaned.loc[1, "listed_price"] == 5.49
    assert pd.isna(cleaned.loc[2, "listed_price"])


# test clean_stock function with various inputs and expected outputs
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("35", 35),
        (" 38 ", 38),
        ("0", 0),
        ("N/A", None),
        ("", None),
        ("invalid", None),
        ("-5", None),
        ("3.5", None),
    ],
)
def test_clean_stock(raw, expected):
    assert clean_stock(raw) == expected


# test if the clean_products function uses clean_stock to normalize the stock_qty column
def test_clean_products_normalizes_stock():
    raw = pd.DataFrame(
        {
            "category": ["Rice & Noodles"] * 4,
            "stock_qty": ["35", "N/A", " 38 ", "-5"],
        }
    )

    cleaned = clean_products(raw)

    assert cleaned["stock_qty"].tolist()[0] == 35
    assert pd.isna(cleaned["stock_qty"].iloc[1])
    assert cleaned["stock_qty"].iloc[2] == 38
    assert pd.isna(cleaned["stock_qty"].iloc[3])
    assert str(cleaned["stock_qty"].dtype) == "Int64"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-10-21", pd.Timestamp("2026-10-21")),
        ("01/11/2026", pd.Timestamp("2026-11-01")),
        ("2026/10/29", pd.Timestamp("2026-10-29")),
        ("2026-11-02T08:12:00", pd.Timestamp("2026-11-02")),
        ("", None),
        ("2026-13-01", None),
        ("2026-02-30", None),
    ],
)
def test_clean_date(raw, expected):
    result = clean_date(raw)

    if expected is None:
        assert result is None
    else:
        assert result == expected


def test_clean_products_normalizes_dates():
    raw = pd.DataFrame(
        {
            "category": ["Beverages"] * 3,
            "last_seen": [
                "2026-10-21",
                "2026-11-02T08:12:00",
                "2026-02-30",
            ],
        }
    )

    cleaned = clean_products(raw)

    assert cleaned.loc[0, "last_seen"] == pd.Timestamp("2026-10-21")
    assert cleaned.loc[1, "last_seen"] == pd.Timestamp("2026-11-02")
    assert pd.isna(cleaned.loc[2, "last_seen"])
    assert pd.api.types.is_datetime64_any_dtype(cleaned["last_seen"])


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("rice & noodles", "Rice & Noodles"),
        ("RICE AND NOODLES", "Rice & Noodles"),
        ("sauces", "Sauces & Condiments"),
        ("drinks", "Beverages"),
        ("Tea & coffee", "Tea & Coffee"),
        ("Unknown", "Unknown"),
    ],
)
def test_clean_category(raw, expected):
    assert clean_category(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Japan", "JP"),
        ("japan", "JP"),
        ("JP", "JP"),
        ("South Korea", "KR"),
        ("Korea", "KR"),
        ("CN", "CN"),
        ("Thailand", "TH"),
        ("Belgium", "BE"),
        ("", None),
    ],
)
def test_clean_country(raw, expected):
    assert clean_country(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("EUR", "EUR"), ("eur", "EUR"), (" USD ", "USD"), ("", None)],
)
def test_clean_currency(raw, expected):
    assert clean_currency(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("yes", True),
        ("TRUE", True),
        ("1", True),
        ("Y", True),
        ("no", False),
        ("False", False),
        ("0", False),
        ("N", False),
        ("unknown", None),
    ],
)
def test_clean_active(raw, expected):
    assert clean_active(raw) == expected


def test_clean_products_normalizes_categorical_fields():
    raw = pd.DataFrame(
        {
            "category": ["drinks"],
            "origin_country": ["Japan"],
            "currency": ["eur"],
            "is_active": ["yes"],
        }
    )

    cleaned = clean_products(raw)

    assert cleaned.loc[0, "category"] == "Beverages"
    assert cleaned.loc[0, "origin_country"] == "JP"
    assert cleaned.loc[0, "currency"] == "EUR"
    assert cleaned.loc[0, "is_active"] == True
    assert str(cleaned["is_active"].dtype) == "boolean"


def test_clean_products_handles_invalid_values_as_missing():
    raw = pd.DataFrame(
        {
            "category": ["Beverages"],
            "listed_price": ["3..49"],
            "stock_qty": ["-3"],
            "last_seen": ["2026-13-01"],
            "is_active": ["unknown"],
        }
    )

    cleaned = clean_products(raw)

    assert pd.isna(cleaned.loc[0, "listed_price"])
    assert pd.isna(cleaned.loc[0, "stock_qty"])
    assert pd.isna(cleaned.loc[0, "last_seen"])
    assert pd.isna(cleaned.loc[0, "is_active"])


def test_deduplicate_products_keeps_latest_and_returns_audit_rows():
    raw = pd.DataFrame(
        {
            "record_id": ["R-1", "R-2", "R-3", "R-4"],
            "sku": ["SYN-1", "SYN-1", "SYN-2", ""],
            "last_seen": [
                pd.Timestamp("2026-10-01"),
                pd.Timestamp("2026-11-01"),
                pd.Timestamp("2026-10-15"),
                pd.Timestamp("2026-11-02"),
            ],
            "listed_price": [1.0, 1.5, 2.0, 3.0],
        }
    )

    deduplicated, duplicate_records = deduplicate_products(raw)

    assert deduplicated["record_id"].tolist() == ["R-2", "R-3", "R-4"]
    assert duplicate_records["record_id"].tolist() == ["R-1", "R-2"]
    assert duplicate_records["selected_as_latest"].tolist() == [False, True]
