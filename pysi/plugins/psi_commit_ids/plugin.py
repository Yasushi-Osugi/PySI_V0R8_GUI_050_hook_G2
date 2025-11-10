# plugins/psi_commit_ids/plugin.py
# PSI コミット（idリスト版）を mutate フェーズで呼び出す

def register(bus):
    def commit(alloc: dict, **ctx):
        week = int(ctx.get("week_idx", 0))
        state, params = ctx.get("state", {}), ctx.get("params", {})

        from pysi.core.psi_bridge_ids import (
            settle_scheduled_events_ids,
            commit_shipments_to_demand_psi_ids,
            commit_replenishment_to_supply_psi_ids
        )

        # 週頭 settle（CO/P → I）
        settle_scheduled_events_ids(state, week)
        # 今週の起票
        commit_shipments_to_demand_psi_ids(alloc, state, params)
        commit_replenishment_to_supply_psi_ids(alloc, state, params)
        return alloc

    # mutate の最後で動かすのが簡潔
    bus.add_filter("plan:allocation:mutate", commit, priority=90)
