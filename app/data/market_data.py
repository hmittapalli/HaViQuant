from __future__ import annotations

try:
    import yfinance as yf
except Exception:
    yf = None
import pandas as pd


class MarketDataService:
    """
    Centralized market-data service.

    The dashboard and analysis engine should always use this
    service instead of calling yfinance directly.
    """

    def get_history(
        self,
        ticker: str,
        period: str = "5y",
    ) -> pd.DataFrame:

        ticker = (
            str(ticker)
            .strip()
            .upper()
        )

        if yf is None:
            raise RuntimeError("yfinance is not installed. Run: python -m pip install -r requirements.txt")

        if not ticker:
            raise ValueError(
                "Ticker symbol cannot be empty."
            )

        try:

            stock = yf.Ticker(ticker)

            data = stock.history(
                period=period,
                auto_adjust=False,
                actions=True,
            )

        except Exception as error:

            raise RuntimeError(
                f"Unable to load market data for "
                f"{ticker}: {error}"
            ) from error

        if data is None or data.empty:

            raise ValueError(
                f"No market data found for {ticker}."
            )

        # --------------------------------------------------
        # Normalize columns
        # --------------------------------------------------

        if isinstance(
            data.columns,
            pd.MultiIndex,
        ):

            data.columns = [
                str(column[0])
                for column in data.columns
            ]

        # --------------------------------------------------
        # Required columns
        # --------------------------------------------------

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        missing_columns = [
            column
            for column in required_columns
            if column not in data.columns
        ]

        if missing_columns:

            raise ValueError(
                f"{ticker} market data is missing "
                f"required columns: "
                f"{', '.join(missing_columns)}"
            )

        # --------------------------------------------------
        # Numeric conversion
        # --------------------------------------------------

        for column in required_columns:

            data[column] = pd.to_numeric(
                data[column],
                errors="coerce",
            )

        # --------------------------------------------------
        # Remove invalid price rows
        # --------------------------------------------------

        data = data.dropna(
            subset=[
                "Open",
                "High",
                "Low",
                "Close",
            ]
        )

        if data.empty:

            raise ValueError(
                f"No valid price data found for {ticker}."
            )

        # --------------------------------------------------
        # Sort chronologically
        # --------------------------------------------------

        data = data.sort_index()

        return data

    def get_latest_price(
        self,
        ticker: str,
    ) -> float:

        data = self.get_history(ticker, period="5d")
        return float(data["Close"].iloc[-1])


if __name__ == "__main__":

    service = MarketDataService()

    ticker = "NVDA"

    data = service.get_history(
        ticker,
        period="5y",
    )

    print(
        f"{ticker}: "
        f"{len(data)} historical rows"
    )

    print(
        f"Latest price: "
        f"${float(data['Close'].iloc[-1]):.2f}"
    )