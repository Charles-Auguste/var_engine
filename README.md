# Data Workflow

## 1. Read Function

The `read` function in `read.py` reads the input Excel file and returns a dictionary of dataframes. It also performs a series of simple unit tests based on the presence or absence of tabs or columns. This function is very restrictive: if it passes, then everything will work.

For the **Market data** tab, the following rules are applied:
- Convert the `Date` column to datetime
- Set the `Date` column as the index
- Convert all other columns to float

For the **Mapping** tab, the following rules are applied:
- Fill `NaN` values with `""`
- Convert all columns to string
- Set the `Md` column as the index

For the **PF** tab, the following rules are applied:
- Fill `NaN` values with `""`
- Convert all columns to string

For the **PF** tab, the following additional rules are applied:
- Convert the `Val` column to float
- Fill `NaN` values in all other columns with `""` and convert to string

## 2. Market Data Preparation

The market data preparation function in `market_data.py` creates all the market data objects. It takes as input market data and mapping dataframes (from the **Market data** and **Mapping** tabs) and returns a dictionary of `<RiskFactor>` objects.

The following rules are applied:
- Default mapping is used if an unknown or empty value is found in the **Mapping** tab, stored in `default_config.py`
- For relative shocks, if a value is equal to 0, a small factor `ADJUSTMENT_REL` stored in `default_config.py` is added (to avoid errors)
- The new market data series are created according to four principles:
  1. The start date (most recent one) is equal to the current date (to match the continuous stream of data the client requires)
  2. The end date (oldest one) is the oldest date of the series
  3. A vector of possible dates is created between the start date and end date following a financial calendar (weekdays). The default is the LSE calendar.
  4. After joining with the list in principle 3, a backfill operation is performed and a data quality score is assigned: 0 for backfilled values and 1 for good values

For instance, assuming the date is January 14, 2025, and the input tab is:

| date       | value |
|------------|-------|
| 12/01/2025 | 0.1   |
| 11/01/2025 | 0.2   |
| 10/01/2025 |       |
| 09/01/2025 | 0.1   |
| 08/01/2025 | 0.05  |
| 07/01/2025 | 0.05  |
| 06/01/2025 | 0.1   |

The code starts by adding `NaN` and joining according to the LSE calendar (removing January 12 - Sunday and January 11 - Saturday):

| date       | value |
|------------|-------|
| 14/01/2025 | NaN   |
| 13/01/2025 | NaN   |
| 10/01/2025 | NaN   |
| 09/01/2025 | 0.1   |
| 08/01/2025 | 0.05  |
| 07/01/2025 | 0.05  |
| 06/01/2025 | 0.1   |

Finally, a backfill operation is performed and a quality score is added:

| date       | value | quality |
|------------|-------|---------|
| 14/01/2025 | 0.1   | 0       |
| 13/01/2025 | 0.1   | 0       |
| 10/01/2025 | 0.1   | 0       |
| 09/01/2025 | 0.1   | 1       |
| 08/01/2025 | 0.05  | 1       |
| 07/01/2025 | 0.05  | 1       |
| 06/01/2025 | 0.1   | 1       |

## 3. PnL Computation

This operation is coded as a lazy one, meaning it is performed once and then the result is stored. This operation tends to be the most time-consuming one. For a given node, there are two possible sources of PnL:

1. PnL due to the sensitivities of this node (A)
2. PnL due to the PnL of all its children (B)

To compute (A) PnL, we assume that values given in the sensitivity tab are absolute. A simple product between the vector of returns and the sensitivity value is computed. If a node has several (A) sensitivities, a simple sum is performed to aggregate them (no correlation).

To compute (B) PnL, we sum PnL vectors without correlation.

## 4. VaR

Starting with a PnL vector, the VaR is computed following those rules:

1. Select a specific range with the window (for instance 3 days)

| date       | PnL   |           Observation    |
|------------|-------|--------------------------|
| 14/01/2025 | 100   | <- Day of VaR estimation |
| 13/01/2025 | -90   |                          |
| 10/01/2025 | -20   |                          |

2. Sort values by PnL

| date       | PnL   |
|------------|-------|
| 14/01/2025 | 100   |
| 10/01/2025 | -20   |
| 13/01/2025 | -90   |

3. Compute a 'step' coefficient and reindex the serie. Here, the step is equal to 100 / (3 - 1) = 50

| index      | PnL   |
|------------|-------|
| 0          | 100   |
| 50         | -20   |
| 100        | -90   |

4. Add a new row that corresponds to percentile * 100. Fill with NaN

| index      | PnL   |
|------------|-------|
| 0          | 100   |
| 50         | -20   |
| 100        | -90   |
| 95         | NaN   |

5. Use pandas interpolation function based on index to estimate VaR

| index      | PnL   |
|------------|-------|
| 0          | 100   |
| 50         | -20   |
| 100        | -90   |
| 95         | -80   |

6. Finally extract VaR value and apply a max formula.

VaR = max(- extracted_value, 0)

Here, the result is 80
