import pandas as pd
import pytest

from src.transformation import clean_date, clean_price, clean_products, clean_stock


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
    assert str(cleaned["last_seen"].dtype) == "datetime64[ns]"
