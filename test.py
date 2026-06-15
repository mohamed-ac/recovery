import pandas as pd
from strategy import ZoneRecoveryStrategy
from backtest import Backtest
from performance import StrategyPerformance1H


# df = pd.read_csv("EURUSD_1H_2020-2024.csv", sep=",", parse_dates=["time"], index_col="time")
# df = df[["open", "high", "low", "close"]]
# df.to_pickle("cache/EURUSD_1H_2020_2024.pkl")



def main():
    #df = pd.read_pickle("cache/EURUSD_1H_2020_2024.pkl")
    
    df = pd.read_pickle("cache/EURUSD_1H_2020_2024.pkl")
    results = []

    for atr_window in [21]:
        for k_inner in [0.5]:
            for k_outer in [1.5]:
                for max_recov in [5]:
                    for recov_multiplier in [1.5]:
                        for risk_pct in [0.1]:
                            print("run start")
                            events = ZoneRecoveryStrategy(
                                df,
                                k_inner=k_inner,
                                k_outer=k_outer,
                                atr_period=atr_window,
                            ).run()
    
                            bt        = Backtest(df, events, max_recov=max_recov, recov_multiplier=recov_multiplier,risk_pct=risk_pct)
                            equity_zr = bt.run()
                            equity_bh = (df["close"] / df["close"].iloc[0]).reindex(equity_zr.index)
    
                            perf_zr = StrategyPerformance1H(equity_zr, "ZoneRecovery").run()
                            perf_bh = StrategyPerformance1H(equity_bh, "BuyAndHold").run()
    
                            results.append({
                                "risk_pct"        : risk_pct,
                                "k_inner"         : k_inner,
                                "k_outer"         : k_outer,
                                "atr_window"      : atr_window,
                                "max_recov"       : max_recov,
                                "recov_multiplier": recov_multiplier,
                                "n_trades"        : bt.n_trades,
                                "win_rate"        : bt.win_rate,
                                "avg_pnl"         : bt.avg_pnl * 100,
                                "n_sl_max_recov"  : bt.n_sl_max_recov,
                                "max_drawdown"    : perf_zr["max_drawdown"],
                                "max_drawdown_bh" : perf_bh["max_drawdown"],
                                "total_return"    : perf_zr["total_return"],
                                "sharpe"          : perf_zr["sharpe"],
                                "cagr"            : perf_zr["cagr"],
                                "cagr_bh"         : perf_bh["cagr"],
                                "diff_vs_bh"      : perf_zr["total_return"] - perf_bh["total_return"],
                            })
                            print("run end")

    results = pd.DataFrame(results)
    breakpoint()

main()