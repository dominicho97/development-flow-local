import pandas as pd


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    # Clean product data

    cleaned = df.copy()

    # Remove whitespace from string columns
    for column in cleaned.select_dtypes(include=["object", "string"]).columns:
        cleaned[column] = cleaned[column].str.strip()

    # Standardize categories
    cleaned["category"] = cleaned["category"].replace(
        {
            "rice & noodles": "Rice & Noodles",
            "RICE AND NOODLES": "Rice & Noodles",
            "Rice/Noodles": "Rice & Noodles",
        }
    )

    # apply clean_price function
    if "listed_price" in cleaned.columns:
        cleaned["listed_price"] = cleaned["listed_price"].map(clean_price)
    return cleaned


def clean_price(value: str) -> float | None:
    # Convert a raw price string into a numeric value.

    value = value.strip().replace("€", "").replace(",", ".")

    if value == "" or value.upper() == "N/A":
        return None

    try:
        return float(value)
    except ValueError:
        return None
