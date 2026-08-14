import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD


class TechnicalAnalysisEngine:

    def analyze(self, data: pd.DataFrame) -> dict:
        if data.empty:
            raise ValueError("No market data available")

        close = data["Close"]

        # Moving averages
        sma_20 = close.rolling(window=20).mean()
        sma_50 = close.rolling(window=50).mean()
        sma_200 = close.rolling(window=200).mean()

        # RSI
        rsi = RSIIndicator(
            close=close,
            window=14
        ).rsi()

        # MACD
        macd_indicator = MACD(close=close)

        macd = macd_indicator.macd()
        macd_signal = macd_indicator.macd_signal()
        macd_histogram = macd_indicator.macd_diff()

        # Volume
        volume = data["Volume"]
        avg_volume_20 = volume.rolling(window=20).mean()

        return {
            "price": float(close.iloc[-1]),
            "sma_20": self._latest_value(sma_20),
            "sma_50": self._latest_value(sma_50),
            "sma_200": self._latest_value(sma_200),
            "rsi": self._latest_value(rsi),
            "macd": self._latest_value(macd),
            "macd_signal": self._latest_value(macd_signal),
            "macd_histogram": self._latest_value(macd_histogram),
            "volume": int(volume.iloc[-1]),
            "avg_volume_20": self._latest_value(avg_volume_20),
        }

    @staticmethod
    def _latest_value(series: pd.Series):
        value = series.iloc[-1]

        if pd.isna(value):
            return None

        return float(value)