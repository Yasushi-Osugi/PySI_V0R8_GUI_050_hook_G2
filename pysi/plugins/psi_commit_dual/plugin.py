# plugins/psi_commit_dual/plugin.py
# PSIコミットHook（demand/supply両方）

def register(bus):
    def commit(alloc: dict, **ctx):
        week = int(ctx.get("week_idx", 0))
        state, params = ctx.get("state", {}), ctx.get("params", {})
        from pysi.core.psi_bridge_dual import (
            settle_scheduled_events_dual,
            commit_shipments_to_demand_psi,
            commit_replenishment_to_supply_psi
        )
        # 週頭イベント決済
        settle_scheduled_events_dual(state, week)
        # demand/supplyコミット
        commit_shipments_to_demand_psi(alloc, state, params)
        commit_replenishment_to_supply_psi(alloc, state, params)
        return alloc

    bus.add_filter("plan:allocation:mutate", commit, priority=90)  # mutateの最後