import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from strategy import ZoneRecoveryStrategy
from backtest import Backtest
from performance import StrategyPerformance1H
from utils import max_theoretical_exposure, max_risk_pct, margin_call_threshold
import time

st.set_page_config(page_title="ZoneRecovery", layout="wide")
st.title("Backtest")


# ── PARAMS ────────────────────────────────────────────────────────────────────
with st.sidebar:
    data_path  = st.text_input("Data path (.pkl)", "cache/EURUSD_1H_2010_2026.pkl")

    k_inner    = st.slider("k_inner", 0.1, 10.0, 1.5, 0.1)
    k_outer    = st.slider("k_outer", 0.1, 15.0, 3.0, 0.1)
    atr_window = st.slider("ATR window", 1, 100, 21)
    max_recov  = st.slider("max_recov", 1, 100, 10)
    recov_mult = st.slider("recov_multiplier", 1.0, 5.0, 1.1, 0.05)
    capital    = st.number_input("Capital (€)", value=10000, step=1000)
    risk_pct   = st.slider("risk_pct", 0.0001, 0.5, 0.01, 0.0001, format="%.4f")
    st.caption(f"Base risk / lot size : {capital * risk_pct:,.2f}€")

    st.markdown("---")
    use_fixed_vol = st.checkbox("Vol marché fixe (au lieu de l'ATR historique)")
    fixed_vol     = None
    if use_fixed_vol:
        fixed_vol = st.number_input("Vol fixe (même unité que le prix, ex: 0.0010)",
                                    value=0.0010, step=0.0001, format="%.4f")

    st.markdown("---")
    max_margin = st.number_input("Marge max autorisée (€)", value=50000, step=1000)

    run_btn = st.button("▶ RUN", use_container_width=True)

# ── RUN ───────────────────────────────────────────────────────────────────────
if run_btn:
    t0 = time.time()
    df = pd.read_pickle(data_path)

    strat = ZoneRecoveryStrategy(df, k_inner=k_inner, k_outer=k_outer, atr_period=atr_window)

    if use_fixed_vol:
        # bypass ATR : vol fixe constante, aucun historique requis
        strat._compute_atr = lambda: pd.Series(fixed_vol, index=df.index)

    events = strat.run()

    bt = Backtest(df, events, max_recov=max_recov, recov_multiplier=recov_mult, capital_init=capital, risk_pct=risk_pct)

    # ── BLOCAGE MARGE MAX ────────────────────────────────────────────────────
    lot_size      = capital * risk_pct
    max_exposure  = sum(lot_size * (recov_mult ** i) for i in range(max_recov + 1))
    margin_called = max_exposure / 30  # levier ESMA 30:1

    if margin_called > max_margin:
        st.error(
            f"Marge appelée estimée ({margin_called:,.0f}€) dépasse la limite "
            f"autorisée ({max_margin:,.0f}€). Backtest bloqué réduire risk_pct, "
            f"max_recov ou recov_multiplier."
        )
        st.stop()

    equity_zr = bt.run()
    equity_bh = (df["close"] / df["close"].iloc[0] * capital).reindex(equity_zr.index)
    perf      = StrategyPerformance1H(equity_zr / capital, "ZR").run()

    # métriques
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Final Equity", f"€{equity_zr.iloc[-1]:,.0f}")
    c2.metric("Sharpe", f"{perf['sharpe']:.3f}")
    c3.metric("CAGR", f"{perf['cagr']*100:.2f}%")
    c4.metric("Max DD", f"{perf['max_drawdown']*100:.1f}%")
    c5.metric("Win Rate", f"{bt.win_rate*100:.1f}% ({bt.n_trades})")

    st.caption(f"Marge appelée estimée : {margin_called:,.0f}€ / {max_margin:,.0f}€ autorisée")

    # equity curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=equity_zr.index, y=equity_zr.values, name="ZoneRecovery", line=dict(color="#ffd54f", width=2)))
    fig.add_trace(go.Scatter(x=equity_bh.index, y=equity_bh.values, name="Buy & Hold",   line=dict(color="#888", width=1, dash="dot")))
    fig.update_layout(template="plotly_dark", height=450, title="Equity Curve")
    st.plotly_chart(fig, use_container_width=True)

    st.caption(f"Run en {time.time()-t0:.1f}s")
