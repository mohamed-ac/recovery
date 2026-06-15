from dataclasses import dataclass
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class Leg:
    """Leg (position)"""
    size: float
    entry_ts: object
    entry_price: float
    origin: str


class Trade:
    """1 trade = Initial Leg + recovery Leg(s)"""

    def __init__(self, ts, entry_price, signal, max_recov, recov_multiplier, lot_size):
        self.max_recov        = max_recov
        self.recov_multiplier = recov_multiplier
        self.lot_size         = lot_size
        self.recov            = 0
        self.is_open          = True
        self.exit_type        = None
        self.pnl              = None

        size = 1.0 if signal == "U1_TOUCHED" else -1.0
        self.legs = [Leg(size, ts, entry_price, "INITIAL")]
        logger.info(f"[{ts}] ENTRY {'LONG' if size > 0 else 'SHORT'} x1")

    @property
    def direction(self) -> int:
        """Sens de la dernière jambe (+1 long / -1 short) """
        return 1 if self.legs[-1].size > 0 else -1

    @property
    def multiplier(self) -> float:
        return self.recov_multiplier ** self.recov

    def recover(self, ts, entry_price, signal):
        """Recovery si recov < max_recov sinon stop loss"""
        if self.recov >= self.max_recov:
            return self.close(ts, entry_price, "SL")
        self.recov += 1
        size = self.multiplier * (-1.0 if signal == "L1_TOUCHED" else 1.0)
        self.legs.append(Leg(size, ts, entry_price, f"RECOVERY_{self.recov}"))
        logger.info(f"[{ts}] RECOVERY {self.recov}/{self.max_recov} x{self.multiplier:.2f}")
        return None

    def close(self, ts, exit_price, exit_type) -> dict:
        self.is_open   = False
        self.exit_type = exit_type
        self.pnl       = self.lot_size * sum(l.size * (exit_price - l.entry_price) for l in self.legs)
        self._log(ts, exit_price)
        first = self.legs[0]
        return {
            "entry_ts"   : first.entry_ts,
            "exit_ts"    : ts,
            "n_positions": len(self.legs),
            "entry_price": first.entry_price,
            "exit_price" : exit_price,
            "pnl"        : self.pnl,
            "exit_type"  : exit_type,
            "origin"     : first.origin,
        }

    def _log(self, ts, exit_price):
        for leg in self.legs:
            pnl = leg.size * (exit_price - leg.entry_price) * self.lot_size
            logger.info(f"  leg size={leg.size:+.2f} | origin={leg.origin} | "
                        f"entry={leg.entry_ts} @ {leg.entry_price:.4f} | "
                        f"exit @ {exit_price:.4f} | pnl={pnl:.4f}€")
        outcome = "WIN" if self.pnl > 0 else "LOSS"
        logger.info(f"[{ts}] {self.exit_type} | origin={self.legs[0].origin} | "
                    f"pnl={self.pnl:.4f}€ {outcome}")
