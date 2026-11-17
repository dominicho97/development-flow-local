import re

import pandas as pd


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    # Clean product data

    cleaned = df.copy()

    # Remove whitespace from string columns
    for column in cleaned.select_dtypes(include=["object", "string"]).columns:
        cleaned[column] = cleaned[column].str.strip()

    if "category" in cleaned.columns:
        cleaned["category"] = cleaned["category"].map(clean_category)

    # apply clean_price function (normalize price)
    if "listed_price" in cleaned.columns:
        cleaned["listed_price"] = cleaned["listed_price"].map(clean_price)

        # apply clean_stock function (normalize stock quantity)
    if "stock_qty" in cleaned.columns:
        cleaned["stock_qty"] = cleaned["stock_qty"].map(clean_stock).astype("Int64")

    # Normalize dates and discard time-of-day values
    if "last_seen" in cleaned.columns:
        cleaned["last_seen"] = cleaned["last_seen"].map(clean_date)

    if "origin_country" in cleaned.columns:
        cleaned["origin_country"] = cleaned["origin_country"].map(clean_country)

    if "currency" in cleaned.columns:
        cleaned["currency"] = cleaned["currency"].map(clean_currency)

    if "is_active" in cleaned.columns:
        cleaned["is_active"] = cleaned["is_active"].map(clean_active).astype("boolean")

    return cleaned


def deduplicate_products(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Keep the latest product row and return duplicate rows for audit.

    Rows with a missing or blank SKU are not deduplicated because there is no
    reliable business key for them. The audit dataframe contains every row in
    a duplicate-SKU group and marks the row selected as the latest observation.
    """

    required_columns = {"sku", "last_seen"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            f"Missing required columns for deduplication: {sorted(missing_columns)}"
        )

    working = df.copy()
    working["_original_order"] = range(len(working))
    valid_sku = working["sku"].notna() & (
        working["sku"].astype("string").str.strip().ne("")
    )
    duplicate_mask = valid_sku & working.duplicated("sku", keep=False)

    candidates = working.loc[valid_sku].sort_values(
        ["sku", "last_seen", "_original_order"],
        ascending=[True, False, True],
        na_position="last",
    )
    selected = candidates.drop_duplicates("sku", keep="first")
    without_sku = working.loc[~valid_sku]

    deduplicated = pd.concat([selected, without_sku]).sort_values("_original_order")
    deduplicated = deduplicated.drop(columns="_original_order").reset_index(drop=True)

    duplicate_records = working.loc[duplicate_mask].copy()
    selected_indexes = set(selected.index)
    duplicate_records["selected_as_latest"] = duplicate_records.index.isin(
        selected_indexes
    )
    duplicate_records = duplicate_records.drop(columns="_original_order")

    return deduplicated, duplicate_records.reset_index(drop=True)


def clean_price(value: str) -> float | None:
    # Convert a raw price string into a numeric value.

    value = value.strip().upper().replace("€", "").replace("EUR", "")
    value = value.strip().replace(",", ".")

    if value == "" or value == "N/A" or value.count(".") > 1:
        return None

    try:
        price = float(value)
        return price if price >= 0 else None
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


def clean_category(value: str | None) -> str | None:
    """Standardize known category aliases while preserving unknown values."""

    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    category_map = {
        "rice & noodles": "Rice & Noodles",
        "rice and noodles": "Rice & Noodles",
        "rice/noodles": "Rice & Noodles",
        "sauces": "Sauces & Condiments",
        "condiments": "Sauces & Condiments",
        "drinks": "Beverages",
        "tea & coffee": "Tea & Coffee",
        "vegetables": "Fresh Produce",
        "seaweed": "Snacks & Seaweed",
    }
    return category_map.get(text.casefold(), text)


def clean_country(value: str | None) -> str | None:
    """Convert country names and aliases to ISO alpha-2 codes."""

    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    country_map = {
        "jp": "JP",
        "japan": "JP",
        "cn": "CN",
        "china": "CN",
        "tw": "TW",
        "taiwan": "TW",
        "th": "TH",
        "thailand": "TH",
        "kr": "KR",
        "korea": "KR",
        "south korea": "KR",
        "vn": "VN",
        "vietnam": "VN",
        "id": "ID",
        "indonesia": "ID",
        "ph": "PH",
        "philippines": "PH",
        "be": "BE",
        "belgium": "BE",
        "nl": "NL",
        "netherlands": "NL",
    }
    return country_map.get(text.casefold(), text.upper() if len(text) == 2 else text)


def clean_currency(value: str | None) -> str | None:
    """Normalize currency codes to uppercase."""

    if value is None:
        return None

    text = str(value).strip()
    if not text or text.upper() in {"N/A", "UNKNOWN"}:
        return None

    return text.upper()


def clean_active(value: str | bool | int | None) -> bool | None:
    """Convert common active flags to nullable booleans."""

    if value is None or pd.isna(value):
        return None

    text = str(value).strip().casefold()
    if text in {"yes", "true", "1", "y"}:
        return True
    if text in {"no", "false", "0", "n"}:
        return False
    return None


def clean_date(value: str | pd.Timestamp | None) -> pd.Timestamp | None:
    """Convert supported date strings to normalized pandas timestamps."""

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()
    if not text:
        return None

    # The source mixes year-first ISO values with day-first slash dates.
    # Parse them with separate rules so invalid month/day values are not
    # silently reinterpreted as a different valid date.
    if re.match(r"^\d{4}[-/]", text):
        parsed = pd.to_datetime(
            text,
            errors="coerce",
            dayfirst=False,
            format="mixed",
        )
    else:
        parsed = pd.to_datetime(
            text,
            errors="coerce",
            dayfirst=True,
            format="mixed",
        )

    if pd.isna(parsed):
        return None

    return parsed.normalize()
