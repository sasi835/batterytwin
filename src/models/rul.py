"""Only observed threshold crossings yield supervised RUL labels; censored cells stay unlabeled."""
import numpy as np

def trend_rul(history, rated_capacity: float, eol_soh: float) -> dict:
    """Descriptive linear trend extrapolation; not a confidence interval or true RUL label."""
    recent = history.tail(20)
    if len(recent)<5:
        return {'trend_cycles':None,'slope_ah_per_cycle':None}
    slope, intercept = np.polyfit(recent.cycle,recent.capacity_ah,1)
    estimate = max(0,(rated_capacity*eol_soh/100-recent.capacity_ah.iloc[-1])/slope) if slope<0 else None
    return {'trend_cycles':float(estimate) if estimate is not None else None,'slope_ah_per_cycle':float(slope)}
