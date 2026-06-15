from enum import Enum


class Action(Enum):
    OPEN_LONG  = "OPEN_LONG"
    OPEN_SHORT = "OPEN_SHORT"
    RECOVERY   = "RECOVERY"
    TP         = "TP"
    SL         = "SL"
    IGNORE     = "IGNORE"


def route(signal: str, trade) -> Action:
    """event ---> ACTION """

    if trade is None:                       # pas en position
        if signal == "U1_TOUCHED":
            return Action.OPEN_LONG
        if signal == "L1_TOUCHED":
            return Action.OPEN_SHORT
        return Action.IGNORE

    if trade.direction > 0:                 # long
        if signal == "L1_TOUCHED":
            return Action.RECOVERY          # Trade décide SL ou recovery
        if signal == "U2_TOUCHED":
            return Action.TP
        return Action.IGNORE

    # short
    if signal == "U1_TOUCHED":
        return Action.RECOVERY
    if signal == "L2_TOUCHED":
        return Action.TP
    return Action.IGNORE
