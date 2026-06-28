"""Tests for the pure Kalshi order-book parsing (kalshi._parse_orderbook / _orderbook_side)."""

from __future__ import annotations

import pytest

from research import kalshi


class TestParseOrderbook:
    def test_yes_centric_inversion_and_scaling(self) -> None:
        # yes = bids to buy YES; no = bids to buy NO (-> YES asks at 100-c cents).
        book = kalshi._parse_orderbook(
            {"yes": [[62, 1200], [61, 800]], "no": [[37, 1500], [36, 900]]}
        )
        assert book is not None
        # YES bids straight from `yes`, cents -> dollars, best (highest) first.
        assert book.bids[0] == pytest.approx((0.62, 1200))
        assert book.best_bid == pytest.approx(0.62)
        assert book.bid_depth == pytest.approx(1200)
        # YES asks derived from `no`: NO bid 37c -> YES ask 63c; best (lowest) first.
        assert book.asks[0] == pytest.approx((0.63, 1500))
        assert book.best_ask == pytest.approx(0.63)
        assert book.ask_depth == pytest.approx(1500)

    def test_one_sided_book_returns_none(self) -> None:
        assert kalshi._parse_orderbook({"yes": [[62, 1200]]}) is None  # no asks
        assert kalshi._parse_orderbook({"no": [[37, 1500]]}) is None   # no bids

    def test_empty_and_null_sides_return_none(self) -> None:
        assert kalshi._parse_orderbook({}) is None
        assert kalshi._parse_orderbook({"yes": None, "no": None}) is None

    def test_depth_sums_duplicate_best_levels(self) -> None:
        book = kalshi._parse_orderbook(
            {"yes": [[62, 1000], [62, 500], [61, 200]], "no": [[40, 300]]}
        )
        assert book is not None
        assert book.best_bid == pytest.approx(0.62)
        assert book.bid_depth == pytest.approx(1500)  # 1000 + 500 at 62c

    def test_out_of_range_and_bad_size_levels_dropped(self) -> None:
        # cents must be strictly inside (0,100); size must be > 0.
        book = kalshi._parse_orderbook(
            {"yes": [[0, 100], [100, 100], [55, 0], [60, 700]], "no": [[30, 400]]}
        )
        assert book is not None
        assert book.bids == [(pytest.approx(0.60), pytest.approx(700))]


class TestOrderbookSide:
    def test_bids_sorted_descending(self) -> None:
        side = kalshi._orderbook_side([[61, 10], [63, 10], [62, 10]], invert=False, dollars=False)
        assert [p for p, _ in side] == pytest.approx([0.63, 0.62, 0.61])

    def test_asks_inverted_and_sorted_ascending(self) -> None:
        # NO bids 37/36 -> YES asks 63/64, best (lowest) first.
        side = kalshi._orderbook_side([[36, 10], [37, 10]], invert=True, dollars=False)
        assert [p for p, _ in side] == pytest.approx([0.63, 0.64])


class TestParseOrderbookDollars:
    """The live `orderbook_fp` schema: yes_dollars/no_dollars as decimal-dollar strings (0-1)."""

    def test_decimal_dollar_two_sided(self) -> None:
        book = kalshi._parse_orderbook(
            {
                "yes_dollars": [["0.6200", "1200.00"], ["0.6100", "800.00"]],
                "no_dollars": [["0.3700", "1500.00"], ["0.3600", "900.00"]],
            }
        )
        assert book is not None
        assert book.best_bid == pytest.approx(0.62)          # yes bid as-is
        assert book.bid_depth == pytest.approx(1200)
        assert book.best_ask == pytest.approx(0.63)          # NO 0.37 -> YES ask 1-0.37
        assert book.ask_depth == pytest.approx(1500)

    def test_deci_cent_prices_supported(self) -> None:
        # Kalshi can quote sub-cent (deci-cent) prices like 0.0010.
        book = kalshi._parse_orderbook(
            {"yes_dollars": [["0.0010", "1000"]], "no_dollars": [["0.0300", "500"]]}
        )
        assert book is not None
        assert book.best_bid == pytest.approx(0.001)
        assert book.best_ask == pytest.approx(0.97)          # 1 - 0.03

    def test_one_sided_dollars_returns_none(self) -> None:
        assert kalshi._parse_orderbook({"yes_dollars": [["0.62", "10"]]}) is None  # no asks
        assert kalshi._parse_orderbook({"no_dollars": [["0.37", "10"]]}) is None   # no bids

    def test_out_of_range_dollars_dropped(self) -> None:
        # dollars must be strictly inside (0,1); size > 0.
        book = kalshi._parse_orderbook(
            {
                "yes_dollars": [["0", "100"], ["1", "100"], ["0.6", "0"], ["0.5", "700"]],
                "no_dollars": [["0.3", "400"]],
            }
        )
        assert book is not None
        assert book.bids == [(pytest.approx(0.5), pytest.approx(700))]
