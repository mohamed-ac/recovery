def max_theoretical_exposure(capital, risk_pct, recov_multiplier, max_recov) -> float:
    """
    1 trade open : N Legs
    total expo = somme lot size des N legs
    without netting
    """
    lot_size = capital * risk_pct
    return sum(lot_size * (recov_multiplier ** i) for i in range(max_recov + 1))


def max_risk_pct(capital, recov_multiplier, max_recov, leverage = 30.0) -> float:
    """
    risk_pct_max = (capital / leverage) / sum(recov_mult^i for i in 0..max_recov)
    """
    expo_factor = sum(recov_multiplier ** i for i in range(max_recov + 1))
    return (capital / leverage) / (capital * expo_factor)


def margin_call_threshold(capital, risk_pct, recov_multiplier, max_recov, leverage= 30.0) -> bool:
    """Retourne True si la config depasse la marge disponible"""
    max_expo   = max_theoretical_exposure(capital, risk_pct, recov_multiplier, max_recov)
    margin_max = capital / leverage
    return max_expo > margin_max


print(max_theoretical_exposure(100000,0.05   ,1.5,10))

