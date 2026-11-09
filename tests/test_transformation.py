import pandas as pd
import pytest

from src.transformation import clean_price, clean_products


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
