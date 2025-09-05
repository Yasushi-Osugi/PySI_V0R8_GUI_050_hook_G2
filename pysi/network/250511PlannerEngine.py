#250511PlannerEngine.py


# core/planner_engine.py

from pysi.plan.demand_generate import convert_monthly_to_weekly
from pysi.plan.operations import set_df_Slots2psi4demand
from pysi.utils.file_io import load_monthly_demand, load_cost_table
from pysi.network.tree import build_tree_from_csv, set_node_costs
from pysi.utils.config import Config

class PlannerEngine:
    def __init__(self, config: Config):
        self.config = config
        self.root_node_outbound = None
        self.nodes_outbound = {}
        self.leaf_nodes_out = []
        self.df_weekly = None

    def load_demand_data(self):
        df_monthly = load_monthly_demand(self.config.MONTHLY_DEMAND_FILE)
        self.df_weekly, plan_range, plan_year_st = convert_monthly_to_weekly(
            df_monthly, self.config.DEFAULT_LOT_SIZE
        )
        return plan_range, plan_year_st

    def load_tree_and_cost(self):
        self.root_node_outbound, self.nodes_outbound = build_tree_from_csv(
            self.config.PROFILE_TREE_OUTBOUND
        )
        cost_table = load_cost_table(self.config.NODE_COST_TABLE_OUTBOUND)
        if cost_table is not None:
            set_node_costs(cost_table, self.nodes_outbound)

    def set_tree(self, root_node, node_dict):
        self.root_node_outbound = root_node
        self.nodes_outbound = node_dict

    def demand_planning(self):
        if self.root_node_outbound is None or self.df_weekly is None:
            print("Error: Tree or demand data not loaded.")
            return
        set_df_Slots2psi4demand(self.root_node_outbound, self.df_weekly)
        print("✅ Demand planning completed.")

    def supply_planning(self):
        # TODO: 実装を追加
        pass

    def eval_buffer_stock(self):
        # TODO: 実装を追加
        pass

    def optimize_network(self):
        # TODO: 実装を追加
        pass


