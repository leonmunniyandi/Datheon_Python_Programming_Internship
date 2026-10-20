# Stock Portfolio Performance Tracker

A Python console application for entering stock holdings, calculating their
performance, and logging portfolio snapshots to CSV.

## Features

- Looks up ticker symbols and company names from the supplied `constituents.txt`.
- Searches stocks by ticker or company name.
- Accepts buy prices and fractional share quantities.
- Combines repeated purchases using their total cost and total shares.
- Calculates invested capital, current market value, gain/loss, and percentage return.
- Uses manual current prices offline, or optional online prices through yfinance.
- Automatically appends dated snapshots to `portfolio_summary.csv`.
- Handles invalid entries, unavailable quotes, and file errors.

## Requirements

Python 3.9 or later. Manual mode uses only Python's standard library.
Keep `portfolio.py` and `constituents.txt` in the same folder.

Although the dataset ends in `.txt`, its contents are CSV. It provides symbols
and company information, **not stock prices**. It is a fixed list and is not
automatically updated when index membership changes.

## Run with manual prices

Open a terminal in this folder and run:

```bash
python portfolio.py
```

Enter a ticker, its buy price per share, and the number of shares purchased.
Repeat for additional purchases, then type `done`. The program asks for one
current price per ticker, displays the result, and saves the CSV automatically.

Use `search apple` to find a company. `BRK.B` and `BRK-B` are both accepted.

## Optional online prices

```bash
python -m pip install -r requirements.txt
python portfolio.py --live
```

Online mode requests the latest available regular-session, unadjusted
one-minute closing price through [yfinance](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.history.html).
The displayed quote timestamp shows when that price was recorded. Prices may
be delayed; when the market is closed, the latest available trading-session
price is used. Quotes refresh when you run a valuation, not continuously.

If a quote or the optional library is unavailable, the program explains the
problem and asks for a manual price. Internet access is required for online mode.

## Example

These are fictional demonstration prices, not actual market quotes:

1. Enter `AAPL`, buy price `150`, shares `10`.
2. Enter `MSFT`, buy price `300`, shares `2`.
3. Enter `done`.
4. Enter current prices `165` for AAPL and `270` for MSFT.

Expected result:

| Holding | Invested (USD) | Market value (USD) | Gain/loss (USD) | Return |
| --- | ---: | ---: | ---: | ---: |
| AAPL | 1,500.00 | 1,650.00 | +150.00 | +10.00% |
| MSFT | 600.00 | 540.00 | -60.00 | -10.00% |
| Total | 2,100.00 | 2,190.00 | +90.00 | +4.29% |

The included `portfolio_summary.csv` contains the fictional example above.
Remove it before your first run if you want a fresh log. Your actual runs create
or append to `portfolio_summary.csv` in the script's folder. Each
run appends a snapshot ID, UTC recording time, one row per holding, and a TOTAL
row. Each holding also records its price source and quote/input timestamp.
Buy price is the cost-weighted average when a ticker has multiple purchases.
The log contains valuations; it does not reload holdings on the next run.

## Calculations

- Invested capital = sum of (buy price x shares) for all purchases.
- Market value = current price x total shares.
- Gain/loss = market value - invested capital.
- Return (%) = gain/loss / invested capital x 100.
- Overall return uses the total gain/loss divided by total invested capital.

Calculations use decimal arithmetic before display rounding. All amounts use
USD; the program does not include fees, dividends, tax, or currency conversion.

## Custom paths

```bash
python portfolio.py --data constituents.txt --output my_summary.csv
```

## Tests

```bash
python -m unittest -v
```

## Files

- `portfolio.py`: main program.
- `constituents.txt`: supplied stock directory, preserved as provided.
- `requirements.txt`: optional dependency for online prices.
- `test_portfolio.py`: calculation, validation, quote handling, and export tests.
- `portfolio_summary.csv`: generated output, initially containing fictional demo prices.
- `.gitignore`: keeps generated logs and Python cache files out of Git commits.
