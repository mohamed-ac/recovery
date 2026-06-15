import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from strategy import ZoneRecoveryStrategy
from backtest import Backtest
from performance import StrategyPerformance1H
from utils import max_theoretical_exposure, max_risk_pct, margin_call_threshold

st.set_page_config(page_title="ZoneRecovery", layout="wide")
st.title("Backtest")

# inputs

with st.sidebar:
    data_path  = st.text_input("Data path (.pkl)", "cache/EURUSD_1H_2010_2026.pkl")
    k_inner    = st.slider("k_inner", 0.5, 3.0, 2.5, 0.1)
    k_outer    = st.slider("k_outer", 1.0, 5.0, 4.0, 0.1)
    atr_window = st.slider("ATR window", 7, 30, 21)
    max_recov  = st.slider("max_recov", 1, 30, 10)
    recov_mult = st.slider("recov_multiplier", 1.0, 3.0, 1.25, 0.05)
    capital    = st.number_input("Capital (€)", value=100000, step=1000)
    risk_pct   = st.number_input("risk_pct", value=0.01, min_value=0.0001,
                                 max_value=0.5, step=0.001, format="%.4f")

    st.caption(f"base_risk = {capital * risk_pct:.2f}€")

    max_expo = max_theoretical_exposure(capital, risk_pct, recov_mult, max_recov)
    safe_pct = max_risk_pct(capital, recov_mult, max_recov)
    if margin_call_threshold(capital, risk_pct, recov_mult, max_recov):
        st.error(f"⛔ MARGIN CALL RISK | max safe risk_pct: {safe_pct*100:.3f}%")
    else:
        st.success(f"✅ Max exposure: €{max_expo:,.2f}")

    run_btn = st.button("▶ RUN", use_container_width=True)

# run
if run_btn:
    try:
        df = pd.read_pickle(data_path)
    except FileNotFoundError:
        st.error(f"Fichier introuvable : {data_path}")
        st.stop()

    events    = ZoneRecoveryStrategy(df, k_inner=k_inner, k_outer=k_outer, atr_period=atr_window).run()
    bt        = Backtest(df, events, max_recov=max_recov, recov_multiplier=recov_mult,
                         capital_init=capital, risk_pct=risk_pct)
    equity_zr = bt.run()
    equity_bh = (df["close"] / df["close"].iloc[0] * capital).reindex(equity_zr.index)
    perf      = StrategyPerformance1H(equity_zr / capital, "ZR").run()

    # metrics
    metrics = [
        ("Sharpe",       f"{perf['sharpe']:.3f}"),
        ("Win Rate",     f"{bt.win_rate*100:.1f}% ({bt.n_trades})"),
        ("Avg Win",      f"{bt.avg_win:.2f}€"),
        ("Avg Loss",     f"{bt.avg_loss:.2f}€"),
        ("Risk/Reward",  f"{bt.RRR:.2f}"),
        ("EV",           f"{bt.EV:.2f}€"),
        ("Max DD",       f"{perf['max_drawdown']*100:.1f}%"),
        ("Final Equity", f"{equity_zr.iloc[-1]:,.0f}€"),
        ("CAGR",         f"{perf['cagr']*100:.2f}%"),
    ]
    for col, (label, val) in zip(st.columns(len(metrics)), metrics):
        col.metric(label, val)

    # eq curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_zr.index, y=equity_zr.values, name="ZoneRecovery",
                             line=dict(color="#ffd54f", width=2)))
    fig.add_trace(go.Scatter(x=equity_bh.index, y=equity_bh.values, name="Buy & Hold",
                             line=dict(color="#888", width=1, dash="dot")))
    fig.update_layout(template="plotly_dark", height=450, title="Equity Curve")
    st.plotly_chart(fig, use_container_width=True)

    # trades grid
    trades = bt.trades
    st.subheader(f"Trades ({len(trades)})")
    if trades.empty:
        st.info("Aucun trade généré.")
    else:
        grid = trades[["entry_ts", "exit_ts", "exit_type", "n_positions",
                       "entry_price", "exit_price", "pnl"]].copy()
        grid["cum_pnl"] = grid["pnl"].cumsum()
        st.dataframe(
            grid,
            use_container_width=True,
            hide_index=True,
            column_config={
                "exit_type":   st.column_config.TextColumn("exit"),
                "n_positions": st.column_config.NumberColumn("legs"),
                "entry_price": st.column_config.NumberColumn(format="%.4f"),
                "exit_price":  st.column_config.NumberColumn(format="%.4f"),
                "pnl":         st.column_config.NumberColumn("PnL (€)", format="%.2f"),
                "cum_pnl":     st.column_config.NumberColumn("Cum PnL (€)", format="%.2f"),
            },
        )

        
        # pnl par trade
        colors = ["#26a69a" if p > 0 else "#ef5350" for p in grid["pnl"]]
        fig = go.Figure(go.Bar(x=grid.index, y=grid["pnl"], marker_color=colors))
        fig.update_layout(template="plotly_dark", height=300, title="PnL par trade")
        st.plotly_chart(fig, use_container_width=True, theme=None)