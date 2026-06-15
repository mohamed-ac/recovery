import pandas as pd
from logger import get_logger
logger = get_logger(__name__)


class ZoneRecoveryStrategy:
    """
    generation d'events (U1/U2/L1/L2 touchés)
    1 event = 1 timestamp + 1 signal
    """
    def __init__(self, df, k_inner=0.5, k_outer=2.5, atr_period=14):
        self.df         = df
        self.k_inner    = k_inner
        self.k_outer    = k_outer
        self.atr_period = atr_period
        self.barriers   = pd.DataFrame(index=df.index, columns=['U2', 'U1', 'L1', 'L2'])

    def _compute_atr(self):
        high  = self.df["high"]
        low   = self.df["low"]
        close = self.df["close"]
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low  - close.shift(1)).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(self.atr_period).mean()

    def run(self) -> pd.DataFrame:
        atr   = self._compute_atr()
        close = self.df["close"]
        high  = self.df["high"]
        low   = self.df["low"]

        events = []

        for i in range(self.atr_period, len(self.df)):
            ref   = close.iloc[i - 1]
            atr_i = atr.iloc[i]

            U2 = ref + atr_i * self.k_outer
            U1 = ref + atr_i * self.k_inner
            L1 = ref - atr_i * self.k_inner
            L2 = ref - atr_i * self.k_outer

            h  = high.iloc[i]
            l  = low.iloc[i]
            ts = self.df.index[i]

            self.barriers.iloc[i] = [U2, U1, L1, L2]

            # SL prioritaire : on checke dans l'ordre SL → TP
            if h >= U2:
                events.append({"ts": ts, "signal": "U2_TOUCHED"})
            elif h >= U1:
                events.append({"ts": ts, "signal": "U1_TOUCHED"})

            if l <= L2:
                events.append({"ts": ts, "signal": "L2_TOUCHED"})
            elif l <= L1:
                events.append({"ts": ts, "signal": "L1_TOUCHED"})

        self.events = pd.DataFrame(events).set_index("ts") if events else pd.DataFrame()
        return self.events