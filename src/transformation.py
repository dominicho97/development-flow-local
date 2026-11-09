import pandas as pd


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    # Clean product data

    cleaned = df.copy()

    for column in cleaned.select_dtypes(include=["object", "string"]).columns:
        cleaned[column] = cleaned[column].str.strip()

    cleaned["category"] = cleaned["category"].replace(
        {
            "rice & noodles": "Rice & Noodles",
            "RICE AND NOODLES": "Rice & Noodles",
            "Rice/Noodles": "Rice & Noodles",
        }
    )

    return cleaned


def clean_price(value: str) -> float | None:
    """Convert a raw price string into a numeric value."""

    value = value.strip().replace("€", "").replace(",", ".")

    if value == "" or value.upper() == "N/A":
        return None

    try:
        return float(value)
    except ValueError:
        return None
