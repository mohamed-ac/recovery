import numpy as np
import pandas as pd
from logger import get_logger
from trade import Trade
from signal_router import route, Action

logger = get_logger(__name__)

HOURS_PER_YEAR = 252 * 24  # ~ barres 1H FX par an


class Backtest:

    def __init__(self, df, events: pd.DataFrame, max_recov=3, recov_multiplier=2,
                 capital_init=10_000, risk_pct=0.01):
        if risk_pct <= 0:
            raise ValueError("risk_pct must be > 0")

        self.df                = df
        self.events            = events
        self.risk_pct          = risk_pct
        self.max_recov         = max_recov
        self.recov_multiplier  = recov_multiplier
        self.capital_init      = capital_init
        self.remaining_capital = capital_init

        self._trades    = pd.DataFrame()
        self._next_open = self.df["open"].shift(-1).fillna(self.df["close"])

        logger.info("BACKTEST START | capital=%s risk_pct=%s recov_mult=%s max_recov=%s",
                    capital_init, risk_pct, recov_multiplier, max_recov)

    # ------------------------------------------------------------------ core
    def build_trades(self):
        trades, trade = [], None
        for ts, row in self.events.iterrows():
            if self.remaining_capital <= 0:
                logger.warning(f"[{ts}] capital épuisé, arrêt")
                break

            signal = row["signal"]
            nxt    = self._next_open.loc[ts]
            action = route(signal, trade)

            if action in (Action.OPEN_LONG, Action.OPEN_SHORT):
                lot_size = self.remaining_capital * self.risk_pct
                trade = Trade(ts, nxt, signal, self.max_recov, self.recov_multiplier, lot_size)

            elif action == Action.RECOVERY:
                closed = trade.recover(ts, nxt, signal)
                if closed:                       # max_recov atteint -> SL
                    self.remaining_capital += closed["pnl"]
                    trades.append(closed)
                    trade = None

            elif action in (Action.TP, Action.SL):
                closed = trade.close(ts, nxt, action.value)
                self.remaining_capital += closed["pnl"]
                trades.append(closed)
                trade = None

        return trades

    def run(self) -> pd.Series:
        if self.events is None or len(self.events) == 0:
            logger.warning("empty events")
            return pd.Series(float(self.capital_init), index=self.df.index)

        self._trades = pd.DataFrame(self.build_trades())
        equity = self._compute_equity()
        max_dd = (equity / equity.cummax() - 1).min()

        logger.info("=" * 60)
        logger.info("  BACKTEST COMPLETE")
        logger.info(f"  trades          : {self.n_trades}")
        logger.info(f"  win_rate        : {self.win_rate:.2%}")
        logger.info(f"  avg_pnl         : {self.avg_pnl:.4f}€")
        logger.info(f"  sharpe/trade    : {self.sharpe_per_trade:.4f}")
        logger.info(f"  n_sl            : {self.n_sl_max_recov}")
        logger.info(f"  final_equity    : {self.get_remaining_capital:.2f}€")
        logger.info(f"  max_drawdown    : {max_dd:.2%}")
        logger.info("=" * 60)
        return equity

    # ------------------------------------------------------------------ equity
    def _compute_equity(self) -> pd.Series:
        equity = pd.Series(float(self.capital_init), index=self.df.index)
        if self._trades.empty:
            return equity
        cum = (self._trades.groupby("exit_ts")["pnl"].sum()
               .sort_index().cumsum()
               .reindex(self.df.index, method="ffill").fillna(0.0))
        return (self.capital_init + cum).clip(lower=0)

    # ------------------------------------------------------------------ metrics
    @property
    def trades(self) -> pd.DataFrame:
        return self._trades

    @property
    def _pnl(self):
        return self._trades["pnl"] if not self._trades.empty else pd.Series(dtype=float)

    @property
    def n_trades(self):
        return len(self._trades)

    @property
    def win_rate(self):
        return (self._pnl > 0).mean() if self.n_trades else 0.0

    @property
    def avg_pnl(self):
        return self._pnl.mean() if self.n_trades else 0.0

    @property
    def n_sl_max_recov(self):
        return int((self._trades["exit_type"] == "SL").sum()) if self.n_trades else 0

    @property
    def get_remaining_capital(self):
        return max(0.0, self.remaining_capital)

    @property
    def avg_win(self):
        w = self._pnl[self._pnl > 0]
        return w.mean() if len(w) else 0.0

    @property
    def avg_loss(self):
        l = self._pnl[self._pnl < 0].abs()
        return l.mean() if len(l) else 0.0

    @property
    def RRR(self):
        return self.avg_win / self.avg_loss if self.avg_loss else 0.0

    @property
    def EV(self):
        return self.win_rate * self.avg_win - (1 - self.win_rate) * self.avg_loss

    @property
    def sharpe_per_trade(self) -> float:
        pnl = self._pnl
        if len(pnl) < 2 or pnl.std() == 0:
            return 0.0
        n_years = len(self.df) / HOURS_PER_YEAR
        return pnl.mean() / pnl.std() * np.sqrt(len(pnl) / n_years)
