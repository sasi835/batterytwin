"""Transparent utilization planning, not unvalidated intervention/lifetime optimization."""
def utilization_plan(remaining_cycles: float, cycles_per_day: float, eol_observed: bool = False) -> dict:
    if cycles_per_day<=0:
        raise ValueError('Cycles per day must be positive')
    remaining=max(0.,remaining_cycles) if not eol_observed else 0.
    scenarios=[{'label':label,'cycles_per_day':rate,'days_to_cycle_budget':remaining/rate} for label,rate in
               [('Lower utilization',cycles_per_day*.75),('Your schedule',cycles_per_day),('Higher utilization',cycles_per_day*1.25)]]
    return {'remaining_cycle_budget':remaining,'cycles_per_day':cycles_per_day,'estimated_days':remaining/cycles_per_day,
            'scenarios':scenarios,'scope':'Arithmetic utilization scenario only. Cycle-life estimate is held fixed. Calendar aging, partial-cycle equivalence, interventions and lifetime gains are not modeled.'}
