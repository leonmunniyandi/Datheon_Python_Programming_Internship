"""Track stock holdings, calculate performance, and append CSV snapshots.

Run ``python portfolio.py`` for manual prices, or add ``--live`` to request
the latest available one-minute market prices through optional yfinance.
"""

import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import sys
from uuid import uuid4


PROJECT_DIR = Path(__file__).resolve().parent
DATASET_PATH = PROJECT_DIR / "constituents.txt"
SUMMARY_PATH = PROJECT_DIR / "portfolio_summary.csv"
ZERO = Decimal("0")
HUNDRED = Decimal("100")
CSV_FIELDS = [
    "snapshot_id", "recorded_at_utc", "symbol", "company", "shares",
    "average_buy_price_usd", "current_price_usd", "invested_usd",
    "market_value_usd", "gain_loss_usd", "gain_loss_percent",
    "price_as_of", "price_source",
]


class PriceLookupError(Exception):
    """Raised when an online market price cannot be retrieved."""


def utc_now():
    """Use explicit UTC timestamps so exported logs are unambiguous."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_constituents(path=DATASET_PATH):
    """The supplied .txt file contains CSV data, including quoted commas."""
    companies = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as dataset:
        reader = csv.DictReader(dataset)
        if not {"Symbol", "Security"}.issubset(reader.fieldnames or []):
            raise ValueError("The dataset must contain Symbol and Security columns.")
        for row in reader:
            symbol = (row.get("Symbol") or "").strip().upper()
            company = (row.get("Security") or "").strip()
            if symbol and company:
                companies[symbol] = company
    if not companies:
        raise ValueError("The dataset does not contain any usable stocks.")
    return companies


def parse_number(text, allow_zero=False):
    """Validate prices/shares and keep decimal arithmetic for calculations."""
    try:
        value = Decimal(text.strip())
    except InvalidOperation:
        raise ValueError("Enter a number such as 150 or 2.5.") from None
    if not value.is_finite():
        raise ValueError("Enter a finite number.")
    if value < ZERO or (value == ZERO and not allow_zero):
        raise ValueError("Enter zero or a positive number." if allow_zero
                         else "Enter a number greater than zero.")
    if value > Decimal("1000000000000") or (ZERO < value < Decimal("0.000001")):
        raise ValueError("Use a value from 0.000001 to 1,000,000,000,000.")
    return value


def read_number(prompt, allow_zero=False):
    while True:
        try:
            return parse_number(input(prompt), allow_zero)
        except ValueError as error:
            print(error)


def add_holding(portfolio, symbol, company, buy_price, shares):
    """Merge repeated purchases by adding shares and their original cost."""
    if symbol not in portfolio:
        portfolio[symbol] = {"company": company, "shares": ZERO, "invested": ZERO}
    portfolio[symbol]["shares"] += shares
    portfolio[symbol]["invested"] += buy_price * shares


def collect_holdings(companies):
    portfolio = {}
    print("Enter a ticker such as AAPL or MSFT.")
    print("Type 'search apple' to find a stock, or 'done' to calculate.\n")
    while True:
        entry = input("Stock ticker: ").strip()
        if entry.lower() == "done":
            return portfolio
        if entry.lower().startswith("search "):
            query = entry[7:].strip().lower()
            matches = [
                (symbol, company) for symbol, company in companies.items()
                if query and (query in symbol.lower() or query in company.lower())
            ]
            for symbol, company in matches[:20]:
                print(f"  {symbol:<8} {company}")
            if not matches:
                print("No matching stocks found.")
            elif len(matches) > 20:
                print("Showing the first 20 matches. Try a more specific search.")
            continue

        # Accept both BRK.B (dataset notation) and BRK-B (Yahoo notation).
        symbol = entry.upper().replace("-", ".")
        if symbol not in companies:
            print("Ticker not found in constituents.txt. Try 'search company name'.")
            continue
        print(f"{symbol}: {companies[symbol]}")
        buy_price = read_number("Buy price per share (USD): ")
        shares = read_number("Number of shares (fractions allowed): ")
        add_holding(portfolio, symbol, companies[symbol], buy_price, shares)
        print("Holding added. Repeated tickers are combined using their total cost.\n")


def fetch_market_price(symbol):
    """Get the latest available unadjusted one-minute closing price.

    The quote includes the bar's timestamp. Prices may be delayed, and the
    latest bar may be from a previous trading session when markets are closed.
    """
    try:
        import yfinance as yf
    except ImportError:
        raise PriceLookupError(
            "Online mode needs yfinance. Run: python -m pip install -r requirements.txt"
        ) from None

    try:
        ticker = yf.Ticker(symbol.replace(".", "-"))
        history = ticker.history(
            period="5d", interval="1m", auto_adjust=False,
            prepost=False, timeout=10,
        )
        if history.empty:
            raise PriceLookupError(f"No recent price was returned for {symbol}.")
        closes = history["Close"].dropna()
        if closes.empty:
            raise PriceLookupError(f"No valid price was returned for {symbol}.")
        price = parse_number(str(closes.iloc[-1]))
        metadata = ticker.get_history_metadata()
        if metadata.get("currency") != "USD":
            raise PriceLookupError(f"The quote currency for {symbol} is not confirmed as USD.")
        return {
            "price": price,
            "as_of": closes.index[-1].isoformat(),
            "source": "Yahoo Finance via yfinance; 1-minute close; may be delayed",
        }
    except PriceLookupError:
        raise
    except Exception as error:
        # Network failures, provider limits, and unavailable symbols can vary
        # by yfinance version; handle them at this external-service boundary.
        raise PriceLookupError(f"Could not fetch a price for {symbol}: {error}") from error


def collect_prices(portfolio, online=False):
    quotes = {}
    for symbol in portfolio:
        if online:
            print(f"\nRequesting a market price for {symbol}...")
            try:
                quotes[symbol] = fetch_market_price(symbol)
                print(f"{symbol}: USD {quotes[symbol]['price']:.4f}")
                print(f"Quote as of: {quotes[symbol]['as_of']}")
                continue
            except PriceLookupError as error:
                print(error)
                print("Enter a price manually to continue, or press Ctrl+C to cancel.")
        price = read_number(f"Current price for {symbol} (USD): ", allow_zero=True)
        quotes[symbol] = {"price": price, "as_of": utc_now(), "source": "Manual input"}
    return quotes


def calculate_summary(portfolio, quotes):
    """Calculate each holding and portfolio totals before display rounding."""
    rows = []
    for symbol, holding in portfolio.items():
        shares = holding["shares"]
        invested = holding["invested"]
        current_price = quotes[symbol]["price"]
        market_value = shares * current_price
        gain_loss = market_value - invested
        rows.append({
            "symbol": symbol,
            "company": holding["company"],
            "shares": shares,
            "average_buy_price_usd": invested / shares,
            "current_price_usd": current_price,
            "invested_usd": invested,
            "market_value_usd": market_value,
            "gain_loss_usd": gain_loss,
            "gain_loss_percent": gain_loss / invested * HUNDRED,
            "price_as_of": quotes[symbol]["as_of"],
            "price_source": quotes[symbol]["source"],
        })
    invested_total = sum((row["invested_usd"] for row in rows), ZERO)
    market_total = sum((row["market_value_usd"] for row in rows), ZERO)
    gain_total = market_total - invested_total
    totals = {
        "invested_usd": invested_total,
        "market_value_usd": market_total,
        "gain_loss_usd": gain_total,
        # Overall return is weighted by invested capital, not averaged.
        "gain_loss_percent": gain_total / invested_total * HUNDRED if invested_total else ZERO,
    }
    return rows, totals


def rounded(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def show_summary(rows, totals):
    print("\nSTOCK PORTFOLIO SUMMARY (USD)")
    print("-" * 107)
    print(f"{'Ticker':<8} {'Shares':>10} {'Avg buy':>12} {'Current':>12} "
          f"{'Invested':>14} {'Value':>14} {'Gain/loss':>14} {'Return':>9}")
    print("-" * 107)
    for row in rows:
        print(f"{row['symbol']:<8} {row['shares']:>10f} "
              f"{rounded(row['average_buy_price_usd']):>12,.2f} "
              f"{rounded(row['current_price_usd']):>12,.2f} "
              f"{rounded(row['invested_usd']):>14,.2f} "
              f"{rounded(row['market_value_usd']):>14,.2f} "
              f"{rounded(row['gain_loss_usd']):>+14,.2f} "
              f"{rounded(row['gain_loss_percent']):>+8.2f}%")
    print("-" * 107)
    print(f"Total invested:     USD {rounded(totals['invested_usd']):,.2f}")
    print(f"Total market value: USD {rounded(totals['market_value_usd']):,.2f}")
    print(f"Total gain/loss:    USD {rounded(totals['gain_loss_usd']):+,.2f}")
    print(f"Overall return:         {rounded(totals['gain_loss_percent']):+.2f}%")
    print("\nPrice sources:")
    for row in rows:
        print(f"  {row['symbol']}: {row['price_source']} | as of {row['price_as_of']}")


def export_summary(rows, totals, path=SUMMARY_PATH):
    """Append a dated snapshot and total row without overwriting older logs."""
    path = Path(path)
    snapshot_id = uuid4().hex
    recorded_at = utc_now()
    # Reject incompatible existing files instead of appending mismatched data.
    needs_header = not path.exists() or path.stat().st_size == 0
    if not needs_header:
        with path.open(newline="", encoding="utf-8") as existing:
            if next(csv.reader(existing), None) != CSV_FIELDS:
                raise ValueError(f"{path.name} has a different CSV header. Choose another output file.")
    records = list(rows) + [{"symbol": "TOTAL", "company": "Portfolio total", **totals}]
    with path.open("a", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
        if needs_header:
            writer.writeheader()
        for row in records:
            record = {"snapshot_id": snapshot_id, "recorded_at_utc": recorded_at, **row}
            for key, value in list(record.items()):
                if isinstance(value, Decimal):
                    # Preserve fractional share and input-price precision.
                    record[key] = format(value, "f") if key in {
                        "shares", "average_buy_price_usd", "current_price_usd"
                    } else format(rounded(value), ".2f")
            writer.writerow(record)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Request online prices using yfinance.")
    parser.add_argument("--data", type=Path, default=DATASET_PATH, help="Path to the constituent CSV/.txt file.")
    parser.add_argument("--output", type=Path, default=SUMMARY_PATH, help="CSV log file to append to.")
    args = parser.parse_args(argv)

    try:
        companies = load_constituents(args.data)
    except (OSError, UnicodeError, csv.Error, ValueError) as error:
        print(f"Cannot load stock dataset: {error}", file=sys.stderr)
        return 1

    print("=" * 45)
    print("     STOCK PORTFOLIO PERFORMANCE TRACKER")
    print("=" * 45)
    print(f"Loaded {len(companies)} stock symbols from {args.data.name}.")
    print("All prices and results use USD.")
    print("Price mode: " + ("Online (latest available; may be delayed)." if args.live else "Manual input."))
    try:
        portfolio = collect_holdings(companies)
        if not portfolio:
            print("No holdings entered. No summary was written.")
            return 0
        quotes = collect_prices(portfolio, online=args.live)
        rows, totals = calculate_summary(portfolio, quotes)
        show_summary(rows, totals)
        try:
            path = export_summary(rows, totals, args.output)
        except (OSError, csv.Error, ValueError) as error:
            print(f"\nThe summary could not be saved: {error}", file=sys.stderr)
            print("Close the CSV if it is open, or use --output with another path.")
            return 1
        print(f"\nSnapshot appended to: {path.resolve()}")
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\nSession cancelled. No completed snapshot was saved.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
