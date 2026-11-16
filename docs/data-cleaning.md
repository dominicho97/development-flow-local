# Data cleaning

`clean_products()` returns a copy of the input dataframe and applies a
transformation only when the corresponding column is present. It does not
change the input dataframe in place.

## Implemented rules

### General text

Whitespace is stripped from object and string columns before field-specific
rules run. Unknown text values are generally preserved after trimming.

### Categories

Known aliases are mapped to canonical labels:

| Input aliases | Canonical value |
| --- | --- |
| `rice & noodles`, `rice and noodles`, `rice/noodles` | `Rice & Noodles` |
| `sauces`, `condiments` | `Sauces & Condiments` |
| `drinks` | `Beverages` |
| `tea & coffee` | `Tea & Coffee` |
| `vegetables` | `Fresh Produce` |
| `seaweed` | `Snacks & Seaweed` |

### Prices

`clean_price()` removes euro symbols and the `EUR` text, accepts comma or dot
decimal separators, and returns a float for parseable values. Empty values,
`N/A`, malformed values, and values with multiple decimal points become
`None`.

Negative prices become `None`; zero remains a valid price. Core transformation
also excludes the latest product observation when its name is missing or
blank, logging the skipped count and preserving the raw row in staging.
Deduplication happens before this filter, so an older named observation is
not substituted for a newer unnamed one.

On each core load, the writer removes existing blank-name core rows and sets
existing negative prices to SQL `NULL` in the same transaction as the upserts.
Other absent products remain untouched. This repairs data loaded before these
rules without changing staging or disabling the Soda checks.

### Stock

`clean_stock()` accepts non-negative integer text and returns a nullable pandas
`Int64` column when used by `clean_products()`. Empty, non-integer, and negative
values become missing values.

### Dates

`clean_date()` supports year-first ISO-style values, day-first slash dates, and
timestamps. It removes the time component and returns a pandas timestamp.
Invalid dates such as `2026-13-01` and `2026-02-30`, as well as blank values,
become missing values.

Year-first values are parsed separately from slash dates so invalid dates are
not silently reinterpreted as a different valid date.

### Countries, currencies, and active status

- Country aliases are normalized to ISO-style alpha-2 codes, such as
  `Japan`/`JP` to `JP` and `South Korea`/`Korea` to `KR`.
- Currency values are trimmed and uppercased; blank, `N/A`, and `UNKNOWN`
  values become missing.
- Active values `yes`, `true`, `1`, and `y` become `True`; `no`, `false`, `0`,
  and `n` become `False`. Other values become missing.

## Duplicate SKU handling

`deduplicate_products()` is a separate operation. It requires `sku` and
`last_seen`, keeps the latest non-empty SKU observation, and uses original row
order as the tie-breaker when dates are equal. Rows with missing or blank SKUs
are retained without deduplication.

The function returns:

1. the selected dataframe; and
2. every row from a duplicate-SKU group, with `selected_as_latest` indicating
   which row was selected.

This preserves conflicting observations for audit instead of silently dropping
them.

## Known limitations and future work

- `clean_products()` does not produce a validation-issue report.
- Duplicate `record_id` values are not handled by the duplicate helper.
- `package_size` is not parsed into quantity and unit fields.
- Product and brand spelling is not corrected beyond whitespace trimming.
- Cleaned data and duplicate audit rows are not written to files by the
  repository's current CLI.
