
from logger import get_logger
logger = get_logger(__name__)
import numpy as np
import pandas as pd

HOURS_PER_YEAR = 252 * 24  # ~6048 heures de trading par an


class StrategyPerformance1H:
    """Input = equity curve horaire (pd.Series)"""

    def __init__(self, equity_curve, strategy_name):
        self.equity_curve  = equity_curve
        self.strategy_name = strategy_name
        self.metrics       = {}
#        logger.info(f"computing metrics {strategy_name}")

    def compute_total_return(self):
        self.metrics["total_return"] = self.equity_curve.iloc[-1] - 1
#        logger.info(f"total_return: {self.metrics['total_return']:.4f}")

    def compute_sharpe_ratio(self):
        returns = self.equity_curve.pct_change().dropna()
        std     = returns.std()
        # annualisation horaire : sqrt(252 * 24)
        sharpe  = np.sqrt(HOURS_PER_YEAR) * (returns.mean() / std) if std != 0 else 0
        self.metrics["sharpe"] = sharpe
#        logger.info(f"sharpe: {self.metrics['sharpe']:.4f}")

    def compute_max_drawdown(self):
        self.metrics["max_drawdown"] = (
            self.equity_curve / self.equity_curve.cummax() - 1
        ).min()
#        logger.info(f"max_drawdown: {self.metrics['max_drawdown']:.4f}")

    def compute_cagr(self):
        """taux de rendement"""
        n_hours      = len(self.equity_curve)
        total_return = self.equity_curve.iloc[-1] - 1
        # annualisation horaire
        self.metrics["cagr"] = (1 + total_return) ** (HOURS_PER_YEAR / n_hours) - 1
#        logger.info(f"cagr: {self.metrics['cagr']:.4f}")

    def compute_calmar(self):
        """calmar ratio : cagr/maxDD"""
        cagr     = self.metrics.get("cagr", 0)
        max_dd   = self.metrics.get("max_drawdown", 0)
        self.metrics["calmar"] = abs(cagr / max_dd) if max_dd != 0 else 0
#        logger.info(f"calmar: {self.metrics['calmar']:.4f}")


    def run(self):
        self.compute_total_return()
        self.compute_sharpe_ratio()
        self.compute_max_drawdown()
        self.compute_cagr()
        self.compute_calmar()
        return self.metrics