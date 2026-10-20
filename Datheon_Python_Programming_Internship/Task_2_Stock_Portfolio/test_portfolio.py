"""Run with python -m unittest -v; no online connection is needed."""

import contextlib
import csv
from datetime import datetime, timezone
from decimal import Decimal
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import portfolio as app


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.holdings = {}
        app.add_holding(self.holdings, "AAPL", "Apple Inc.", Decimal("150"), Decimal("10"))
        app.add_holding(self.holdings, "MSFT", "Microsoft", Decimal("300"), Decimal("2"))
        self.quotes = {
            "AAPL": {"price": Decimal("165"), "as_of": "demo", "source": "Manual input"},
            "MSFT": {"price": Decimal("270"), "as_of": "demo", "source": "Manual input"},
        }

    def temporary_folder(self):
        # Keep test fixtures inside the writable project directory.
        temporary = tempfile.TemporaryDirectory(dir=app.PROJECT_DIR)
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def test_supplied_csv_dataset(self):
        companies = app.load_constituents()
        self.assertGreater(len(companies), 400)
        self.assertEqual(companies["AAPL"], "Apple Inc.")
        self.assertIn("BRK.B", companies)
        self.assertIn("GOOG", companies)
        self.assertIn("GOOGL", companies)

    def test_invalid_prices_and_shares(self):
        for invalid in ("", "abc", "$20", "0", "-1", "NaN", "sNaN", "Infinity", "-Infinity"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                app.parse_number(invalid)
        self.assertEqual(app.parse_number(" 2.5 "), Decimal("2.5"))
        self.assertEqual(app.parse_number("0", allow_zero=True), Decimal("0"))

    def test_mixed_gains_and_capital_weighted_return(self):
        rows, totals = app.calculate_summary(self.holdings, self.quotes)
        self.assertEqual(rows[0]["gain_loss_usd"], Decimal("150"))
        self.assertEqual(rows[1]["gain_loss_percent"], Decimal("-10"))
        self.assertEqual(totals["invested_usd"], Decimal("2100"))
        self.assertEqual(totals["market_value_usd"], Decimal("2190"))
        self.assertEqual(totals["gain_loss_usd"], Decimal("90"))
        self.assertEqual(app.rounded(totals["gain_loss_percent"]), Decimal("4.29"))

    def test_repeat_purchases_use_weighted_cost_and_fractional_shares(self):
        holdings = {}
        app.add_holding(holdings, "AAPL", "Apple", Decimal("100"), Decimal("1.5"))
        app.add_holding(holdings, "AAPL", "Apple", Decimal("200"), Decimal("0.5"))
        quotes = {"AAPL": {"price": Decimal("120"), "as_of": "demo", "source": "Manual input"}}
        rows, totals = app.calculate_summary(holdings, quotes)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["shares"], Decimal("2"))
        self.assertEqual(rows[0]["average_buy_price_usd"], Decimal("125"))
        self.assertEqual(totals["gain_loss_usd"], Decimal("-10"))
        self.assertEqual(totals["gain_loss_percent"], Decimal("-4"))

    def test_zero_current_price_is_a_total_loss(self):
        self.quotes["AAPL"]["price"] = Decimal("0")
        rows, _ = app.calculate_summary(self.holdings, self.quotes)
        self.assertEqual(rows[0]["gain_loss_usd"], Decimal("-1500"))
        self.assertEqual(rows[0]["gain_loss_percent"], Decimal("-100"))

    def test_empty_summary_has_no_division_error(self):
        rows, totals = app.calculate_summary({}, {})
        self.assertEqual(rows, [])
        self.assertEqual(totals["gain_loss_percent"], Decimal("0"))

    def test_csv_appends_snapshots_and_quotes_company_names(self):
        path = self.temporary_folder() / "summary.csv"
        self.holdings["AAPL"]["company"] = "Example, Incorporated"
        rows, totals = app.calculate_summary(self.holdings, self.quotes)
        app.export_summary(rows, totals, path)
        app.export_summary(rows, totals, path)
        with path.open(newline="", encoding="utf-8") as saved:
            reader = csv.DictReader(saved)
            self.assertEqual(reader.fieldnames, app.CSV_FIELDS)
            records = list(reader)
        self.assertEqual(len(records), 6)
        self.assertEqual(records[0]["company"], "Example, Incorporated")
        self.assertEqual(records[2]["symbol"], "TOTAL")
        self.assertEqual(records[2]["gain_loss_usd"], "90.00")
        self.assertEqual(records[5]["gain_loss_percent"], "4.29")
        self.assertNotEqual(records[0]["snapshot_id"], records[3]["snapshot_id"])

    def test_incompatible_existing_csv_is_preserved(self):
        path = self.temporary_folder() / "other.csv"
        original = "a,b\n1,2\n"
        path.write_text(original, encoding="utf-8")
        rows, totals = app.calculate_summary(self.holdings, self.quotes)
        with self.assertRaises(ValueError):
            app.export_summary(rows, totals, path)
        self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_missing_and_malformed_datasets(self):
        path = self.temporary_folder() / "stocks.txt"
        with self.assertRaises(OSError):
            app.load_constituents(path)
        path.write_text("wrong,columns\nAAPL,Apple\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            app.load_constituents(path)
        path.write_text("Symbol,Security\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            app.load_constituents(path)

    def test_online_symbol_conversion_timestamp_and_unadjusted_prices(self):
        provider = MagicMock()
        ticker = provider.Ticker.return_value
        history = ticker.history.return_value
        history.empty = False
        closes = history.__getitem__.return_value.dropna.return_value
        closes.empty = False
        closes.iloc.__getitem__.return_value = 123.45
        closes.index.__getitem__.return_value = datetime(2026, 1, 2, tzinfo=timezone.utc)
        ticker.get_history_metadata.return_value = {"currency": "USD"}
        with patch.dict(sys.modules, {"yfinance": provider}):
            quote = app.fetch_market_price("BRK.B")
        provider.Ticker.assert_called_once_with("BRK-B")
        self.assertFalse(ticker.history.call_args.kwargs["auto_adjust"])
        self.assertEqual(quote["price"], Decimal("123.45"))
        self.assertEqual(quote["as_of"], "2026-01-02T00:00:00+00:00")

    def test_online_unavailable_data_and_network_errors(self):
        provider = MagicMock()
        provider.Ticker.return_value.history.return_value.empty = True
        with patch.dict(sys.modules, {"yfinance": provider}):
            with self.assertRaises(app.PriceLookupError):
                app.fetch_market_price("AAPL")
            provider.Ticker.return_value.history.side_effect = ConnectionError("Offline")
            with self.assertRaises(app.PriceLookupError):
                app.fetch_market_price("AAPL")

    def test_missing_optional_library_and_manual_fallback(self):
        with patch.dict(sys.modules, {"yfinance": None}):
            with self.assertRaises(app.PriceLookupError):
                app.fetch_market_price("AAPL")
        with patch.object(app, "fetch_market_price", side_effect=app.PriceLookupError("Offline")):
            with patch("builtins.input", return_value="155.50"), contextlib.redirect_stdout(io.StringIO()):
                quotes = app.collect_prices({"AAPL": {}}, online=True)
        self.assertEqual(quotes["AAPL"]["price"], Decimal("155.50"))
        self.assertEqual(quotes["AAPL"]["source"], "Manual input")


if __name__ == "__main__":
    unittest.main()
