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

    # apply clean_price function (normalize price)
    if "listed_price" in cleaned.columns:
        cleaned["listed_price"] = cleaned["listed_price"].map(clean_price)

        # apply clean_stock function (normalize stock quantity)
    if "stock_qty" in cleaned.columns:
        cleaned["stock_qty"] = cleaned["stock_qty"].map(clean_stock).astype("Int64")

    # Normalize dates and discard time-of-day values
    if "last_seen" in cleaned.columns:
        cleaned["last_seen"] = cleaned["last_seen"].map(clean_date)

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


def clean_stock(value: str) -> int | None:
    # Convert a raw stock quantity into a non-negative integer.
    # example: ["35", "N/A", " 38 ", "-5"] to [35, <NA>, 38, <NA>]

    value = value.strip()

    try:
        quantity = int(value)
    except ValueError:
        return None

    return quantity if quantity >= 0 else None


def clean_date(value: str | pd.Timestamp | None) -> pd.Timestamp | None:
    """Convert supported date strings to normalized pandas timestamps."""

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    parsed = pd.to_datetime(
        text,
        errors="coerce",
        dayfirst=True,
        format="mixed",
    )

    if pd.isna(parsed):
        return None

    return parsed.normalize()
