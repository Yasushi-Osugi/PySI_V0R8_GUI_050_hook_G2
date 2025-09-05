#network_tree250114.py


# network/tree.py
from typing import List, Dict, Optional

from collections import defaultdict

from pysi.utils.file_io import read_tree_file
#from some_module import Node  # Nodeクラスを適切な場所からインポート

#from pysi.plan.demand_processing import *
#from plan.demand_processing import shiftS2P_LV

from pysi.plan.operations import *
#from pysi.plan.operations import calcS2P, set_S2psi, get_set_childrenP2S2psi


## 2 Nodeクラスの拡張
#class Node:
#    def __init__(self, node_name):
#        self.node_name = node_name
#        self.sku_dict = {}  # product_name → SKU





class Node:
    def __init__(self, name: str):
        self.name = name
        self.children: List['Node'] = []
        self.parent: Optional['Node'] = None

        # node position on network
        self.depth = 0
        self.width = 0


        # Geographic Position
        self.longitude = None
        self.latitude  = None



        # *******************
        # SKU linkage
        # *******************
        self.sku_dict = {}  # product_name 2 SKU


        # *******************
        # PSI attribute move Node 2 SKU
        # *******************
        self.lot_size = 1  # default setting
        self.psi = []  # Placeholder for PSI data

        self.iso_week_demand = None  # Original demand converted to ISO week
        self.psi4demand = None
        self.psi4supply = None
        self.psi4couple = None
        self.psi4accume = None

        self.plan_range = 1
        self.plan_year_st = 2025

        self.safety_stock_week = 0
        self.long_vacation_weeks = []


        # Evaluation
        self.decoupling_total_I = []  # total Inventory all over the plan


        # "lot_counts" is the bridge PSI2EVAL
        self.lot_counts = [0 for x in range(0, 53 * self.plan_range)]
        self.lot_counts_all = 0  # sum(self.lot_counts)



        # *******************
        # Value attribute move Node 2 SKU
        # *******************

        # For NetworkX optimise that is NOT applied now
        self.leadtime = 1   # same as safety_stock_week
        self.nx_demand = 1  # weekly average demand by lot
        self.nx_weight = 1  # move_cost_all_to_nodeB (from nodeA to nodeB)
        self.nx_capacity = 1  # lot by lot


        # Settings for cost-profit evaluation parameter
        self.LT_boat = 1
        self.SS_days = 7
        self.HS_code = ""
        self.customs_tariff_rate = 0
        self.tariff_on_price = 0
        self.price_elasticity = 0


        # ******************************
        # evaluation data initialise rewardsを計算の初期化
        # ******************************

        # ******************************
        # Profit_Ratio #float
        # ******************************
        self.eval_profit_ratio = Profit_Ratio = 0.6

        # Revenue, Profit and Costs
        self.eval_revenue = 0
        self.eval_profit = 0


        self.eval_PO_cost = 0
        self.eval_P_cost = 0
        self.eval_WH_cost = 0
        self.eval_SGMC = 0
        self.eval_Dist_Cost = 0



        # ******************************
        # set_EVAL_cash_in_data #list for 53weeks * 5 years # 5年を想定
        # *******************************
        self.Profit = Profit = [0 for i in range(53 * self.plan_range)]
        self.Week_Intrest = Week_Intrest = [0 for i in range(53 * self.plan_range)]
        self.Cash_In = Cash_In = [0 for i in range(53 * self.plan_range)]
        self.Shipped_LOT = Shipped_LOT = [0 for i in range(53 * self.plan_range)]
        self.Shipped = Shipped = [0 for i in range(53 * self.plan_range)]

        # ******************************
        # set_EVAL_cash_out_data #list for 54 weeks
        # ******************************

        self.SGMC = SGMC = [0 for i in range(53 * self.plan_range)]
        self.PO_manage = PO_manage = [0 for i in range(53 * self.plan_range)]
        self.PO_cost = PO_cost = [0 for i in range(53 * self.plan_range)]
        self.P_unit = P_unit = [0 for i in range(53 * self.plan_range)]
        self.P_cost = P_cost = [0 for i in range(53 * self.plan_range)]

        self.I = I = [0 for i in range(53 * self.plan_range)]

        self.I_unit = I_unit = [0 for i in range(53 * self.plan_range)]
        self.WH_cost = WH_cost = [0 for i in range(53 * self.plan_range)]
        self.Dist_Cost = Dist_Cost = [0 for i in range(53 * self.plan_range)]



        # Cost structure demand
        self.price_sales_shipped = 0
        self.cost_total = 0
        self.profit = 0
        self.marketing_promotion = 0
        self.sales_admin_cost = 0
        self.SGA_total = 0
        self.custom_tax = 0
        self.tax_portion = 0
        self.logistics_costs = 0
        self.warehouse_cost = 0
        self.direct_materials_costs = 0
        self.purchase_total_cost = 0
        self.prod_indirect_labor = 0
        self.prod_indirect_others = 0
        self.direct_labor_costs = 0
        self.depreciation_others = 0
        self.manufacturing_overhead = 0

        # Profit accumulated root to node
        self.cs_profit_accume = 0

        # Cost Structure
        self.cs_price_sales_shipped = 0
        self.cs_cost_total = 0
        self.cs_profit = 0
        self.cs_marketing_promotion = 0
        self.cs_sales_admin_cost = 0
        self.cs_SGA_total = 0

        #self.cs_custom_tax = 0 # stop tariff_rate

        self.cs_tax_portion = 0
        self.cs_logistics_costs = 0
        self.cs_warehouse_cost = 0
        self.cs_direct_materials_costs = 0
        self.cs_purchase_total_cost = 0
        self.cs_prod_indirect_labor = 0
        self.cs_prod_indirect_others = 0
        self.cs_direct_labor_costs = 0
        self.cs_depreciation_others = 0
        self.cs_manufacturing_overhead = 0

        # Evaluated cost = Cost Structure X lot_counts
        self.eval_cs_price_sales_shipped = 0  # revenue
        self.eval_cs_cost_total = 0  # cost
        self.eval_cs_profit = 0  # profit
        self.eval_cs_marketing_promotion = 0
        self.eval_cs_sales_admin_cost = 0
        self.eval_cs_SGA_total = 0

        #self.eval_cs_custom_tax = 0 # stop tariff rate

        self.eval_cs_tax_portion = 0
        self.eval_cs_logistics_costs = 0
        self.eval_cs_warehouse_cost = 0
        self.eval_cs_direct_materials_costs = 0
        self.eval_cs_purchase_total_cost = 0
        self.eval_cs_prod_indirect_labor = 0
        self.eval_cs_prod_indirect_others = 0
        self.eval_cs_direct_labor_costs = 0
        self.eval_cs_depreciation_others = 0
        self.eval_cs_manufacturing_overhead = 0

        # Shipped lots count W / M / Q / Y / LifeCycle
        self.shipped_lots_W = []  # 53*plan_range
        self.shipped_lots_M = []  # 12*plan_range
        self.shipped_lots_Q = []  # 4*plan_range
        self.shipped_lots_Y = []  # 1*plan_range
        self.shipped_lots_L = []  # 1  # lifecycle a year

        # Planned Amount
        self.amt_price_sales_shipped = []    # Revenue cash_IN???
        self.amt_cost_total = []
        self.amt_profit = []                 # Profit
        self.amt_marketing_promotion = []
        self.amt_sales_admin_cost = []
        self.amt_SGA_total = []
        self.amt_custom_tax = []
        self.amt_tax_portion = []
        self.amt_logistiamt_costs = []
        self.amt_warehouse_cost = []
        self.amt_direct_materials_costs = [] # FOB@port 
        self.amt_purchase_total_cost = []    # 
        self.amt_prod_indirect_labor = []
        self.amt_prod_indirect_others = []
        self.amt_direct_labor_costs = []
        self.amt_depreciation_others = []
        self.amt_manufacturing_overhead = []

        # Shipped amt W / M / Q / Y / LifeCycle
        self.shipped_amt_W = []  # 53*plan_range
        self.shipped_amt_M = []  # 12*plan_range
        self.shipped_amt_Q = []  # 4*plan_range
        self.shipped_amt_Y = []  # 1*plan_range
        self.shipped_amt_L = []  # 1  # lifecycle a year

        # Control FLAGs
        self.cost_standard_flag = 0
        self.PSI_graph_flag = "OFF"
        self.buffering_stock_flag = "OFF"

        self.revenue = 0
        self.profit  = 0

        self.AR_lead_time = 0 # Accounts Receivable 売掛
        self.AP_lead_time = 0 # Accounts Payable 買掛




    # ***********************
    # SKU linkage
    # ***********************
    def add_sku(self, product_name: str):
        sku = SKU(product_name, self.name)
        self.sku_dict[product_name] = sku
        return sku

    def get_sku(self, product_name):
        return self.sku_dict[product_name]



    def add_child(self, child: 'Node'):
        """Add a child node to the current node."""
        self.children.append(child)
        child.parent = self

    def set_depth(self, depth: int):
        """Recursively set the depth of the node and its children."""
        self.depth = depth
        for child in self.children:
            child.set_depth(depth + 1)

    def print_tree(self, level: int = 0):
        """Print the tree structure starting from the current node."""
        print("  " * level + f"Node: {self.name}")
        for child in self.children:
            child.print_tree(level + 1)



    # ********************************
    # ココで属性をセット@240417
    # ********************************
    def set_attributes(self, row):

        #print("set_attributes(self, row):", row)
        # self.lot_size = int(row[3])
        # self.leadtime = int(row[4])  # 前提:SS=0
        # self.long_vacation_weeks = eval(row[5])

        self.lot_size = int(row["lot_size"])

        # ********************************
        # with using NetworkX
        # ********************************

        # weightとcapacityは、edge=(node_A,node_B)の属性でnodeで一意ではない

        self.leadtime = int(row["leadtime"])  # 前提:SS=0 # "weight"4NetworkX
        self.capacity = int(row["process_capa"])  # "capacity"4NetworkX

        self.long_vacation_weeks = eval(row["long_vacation_weeks"])

        # **************************
        # BU_SC_node_profile     business_unit_supplychain_node
        # **************************

        # @240421 機械学習のフラグはstop
        ## **************************
        ## plan_basic_parameter ***sequencing is TEMPORARY
        ## **************************
        #        self.PlanningYear           = row['plan_year']
        #        self.plan_engine            = row['plan_engine']
        #        self.reward_sw              = row['reward_sw']

        # 多段階PSIのフラグはstop
        ## ***************************
        ## business unit identify
        ## ***************************
        #        self.product_name           = row['product_name']
        #        self.SC_tree_id             = row['SC_tree_id']
        #        self.node_from              = row['node_from']
        #        self.node_to                = row['node_to']


        # ***************************
        # ココからcost-profit evaluation 用の属性セット
        # ***************************
        self.LT_boat = float(row["LT_boat"])



        self.SS_days = float(row["SS_days"])


        print("row[ customs_tariff_rate ]", row["customs_tariff_rate"])



        self.HS_code              = str(row["HS_code"])
        self.customs_tariff_rate  = float(row["customs_tariff_rate"])
        self.price_elasticity     = float(row["price_elasticity"])



        self.cost_standard_flag   = float(row["cost_standard_flag"])


        self.AR_lead_time   = float(row["AR_lead_time"])
        self.AP_lead_time   = float(row["AP_lead_time"])


        self.PSI_graph_flag       = str(row["PSI_graph_flag"])
        self.buffering_stock_flag = str(row["buffering_stock_flag"])

        self.base_leaf = None






    def set_parent(self):
        # def set_parent(self, node):

        # treeを辿りながら親ノードを探索
        if self.children == []:
            pass
        else:
            for child in self.children:
                child.parent = self
                # child.parent = node




    def set_cost_attr(
        self,
        price_sales_shipped,
        cost_total,
        profit,
        marketing_promotion=None,
        sales_admin_cost=None,
        SGA_total=None,

        #custom_tax=None,
        #tax_portion=None,

        logistics_costs=None,
        warehouse_cost=None,
        direct_materials_costs=None,
        purchase_total_cost=None,
        prod_indirect_labor=None,
        prod_indirect_others=None,
        direct_labor_costs=None,
        depreciation_others=None,
        manufacturing_overhead=None,
    ):

        # self.node_name = node_name # node_name is STOP

        self.price_sales_shipped = price_sales_shipped
        self.cost_total = cost_total
        self.profit = profit
        self.marketing_promotion = marketing_promotion
        self.sales_admin_cost = sales_admin_cost
        self.SGA_total = SGA_total

        #self.custom_tax = custom_tax
        #self.tax_portion = tax_portion

        self.logistics_costs = logistics_costs
        self.warehouse_cost = warehouse_cost
        self.direct_materials_costs = direct_materials_costs
        self.purchase_total_cost = purchase_total_cost
        self.prod_indirect_labor = prod_indirect_labor
        self.prod_indirect_others = prod_indirect_others
        self.direct_labor_costs = direct_labor_costs
        self.depreciation_others = depreciation_others
        self.manufacturing_overhead = manufacturing_overhead


    def normalize_cost(self):

        cost_total = self.add_tax_sum_cost()

        # self.node_name = node_name # node_name is STOP


        self.direct_materials_costs = self.direct_materials_costs / cost_total

        #self.custom_tax = custom_tax # STOP this is rate 
        self.tax_portion            = self.tax_portion            / cost_total

        self.profit                 = self.profit                 / cost_total
        self.marketing_promotion    = self.marketing_promotion    / cost_total
        self.sales_admin_cost       = self.sales_admin_cost       / cost_total
        self.logistics_costs        = self.logistics_costs        / cost_total
        self.warehouse_cost         = self.warehouse_cost         / cost_total
        self.prod_indirect_labor    = self.prod_indirect_labor    / cost_total
        self.prod_indirect_others   = self.prod_indirect_others   / cost_total
        self.direct_labor_costs     = self.direct_labor_costs     / cost_total
        self.depreciation_others    = self.depreciation_others    / cost_total
                                       


        self.SGA_total              = ( self.marketing_promotion
                                    + self.sales_admin_cost )

        self.purchase_total_cost    = ( self.logistics_costs
                                    + self.warehouse_cost 
                                    + self.direct_materials_costs 
                                    + self.tax_portion )

        self.manufacturing_overhead = ( self.prod_indirect_labor 
                                    +  self.prod_indirect_others
                                    +  self.direct_labor_costs  
                                    +  self.depreciation_others )


        self.cost_total             = ( self.purchase_total_cost
                                    + self.SGA_total
                                    + self.manufacturing_overhead )

        self.price_sales_shipped    = self.cost_total + self.profit


    def add_tax_sum_cost(self):


        # calc_custom_tax
        self.tax_portion = self.direct_materials_costs * self.customs_tariff_rate


        cost_total = 0
        cost_total = (
            self.direct_materials_costs

            # this is CUSTOM_TAX 
            #+ self.direct_materials_costs * self.customs_tariff_rate
            + self.tax_portion


            + self.marketing_promotion
            + self.sales_admin_cost

            + self.logistics_costs
            + self.warehouse_cost
            + self.prod_indirect_labor
            + self.prod_indirect_others
            + self.direct_labor_costs
            + self.depreciation_others
            + self.profit
        )
        print("cost_total", self.name, cost_total)
        return cost_total


    def print_cost_attr(self):

        # self.node_name = node_name # node_name is STOP
        print("self.price_sales_shipped", self.price_sales_shipped)
        print("self.cost_total", self.cost_total)
        print("self.profit", self.profit)
        print("self.marketing_promotion", self.marketing_promotion)
        print("self.sales_admin_cost", self.sales_admin_cost)
        print("self.SGA_total", self.SGA_total)

        #print("self.custom_tax", self.custom_tax)
        #print("self.tax_portion", self.tax_portion)

        print("self.logistics_costs", self.logistics_costs)
        print("self.warehouse_cost", self.warehouse_cost)
        print("self.direct_materials_costs", self.direct_materials_costs)
        print("self.purchase_total_cost", self.purchase_total_cost)
        print("self.prod_indirect_labor", self.prod_indirect_labor)
        print("self.prod_indirect_others", self.prod_indirect_others)
        print("self.direct_labor_costs", self.direct_labor_costs)
        print("self.depreciation_others", self.depreciation_others)
        print("self.manufacturing_overhead", self.manufacturing_overhead)





    def set_plan_range_lot_counts(self, plan_range, plan_year_st):

        # print("node.plan_range", self.name, self.plan_range)

        self.plan_range = plan_range
        self.plan_year_st = plan_year_st

        self.lot_counts = [0 for x in range(0, 53 * self.plan_range)]


        for child in self.children:

            child.set_plan_range_lot_counts(plan_range, plan_year_st)







# ****************************
# PSI planning operation on tree
# ****************************

    def set_S2psi(self, pSi):

        # S_lots_listが辞書で、node.psiにセットする

        # print("len(self.psi4demand) = ", len(self.psi4demand) )
        # print("len(pSi) = ", len(pSi) )

        for w in range(len(pSi)):  # Sのリスト

            self.psi4demand[w][0].extend(pSi[w])



    def calcS2P(self): # backward planning

        # **************************
        # Safety Stock as LT shift
        # **************************
        # leadtimeとsafety_stock_weekは、ここでは同じ

        # 同一node内なので、ssのみで良い
        shift_week = int(round(self.SS_days / 7))

        ## stop 同一node内でのLT shiftは無し
        ## SS is rounded_int_num
        # shift_week = self.leadtime +  int(round(self.SS_days / 7))

        # **************************
        # long vacation weeks
        # **************************
        lv_week = self.long_vacation_weeks

        # 同じnode内でのS to P の計算処理 # backward planning
        self.psi4demand = shiftS2P_LV(self.psi4demand, shift_week, lv_week)

        pass



    # psi4demand にセットした lot を、psi4supply にも初期転写
    def copy_demand_to_supply(self): # in backward planning process

        plan_len = 53 * self.plan_range

        for w in range(0, plan_len):  

            lots_list = self.psi4demand[w][0]
            self.psi4supply[w][0].extend(lots_list)

            #lot_counts = len(self.psi4demand[w][0]) 
            #
            #for lot in range(lot_counts):
            #    self.psi4supply[w][0].extend(self.psi4demand[w][0][lot])





    def get_set_childrenP2S2psi(self, plan_range):

        for child in self.children:

            for w in range(self.leadtime, 53 * plan_range):

                # ******************
                # logistics LT switch
                # ******************
                # 物流をnodeとして定義する場合の表現 STOP
                # 子node childのP [3]のweek positionを親node selfのS [0]にset
                # self.psi4demand[w][0].extend(child.psi4demand[w][3])

                # 物流をLT_shiftで定義する場合の表現 GO
                # childのPのweek positionをLT_shiftして、親nodeのS [0]にset
                ws = w - self.leadtime
                self.psi4demand[ws][0].extend(child.psi4demand[w][3])




    # ******************
    # for debug
    # ******************
    def show_sum_cs(self):

        cs_sum = 0

        cs_sum = (
            self.cs_direct_materials_costs
            + self.cs_marketing_promotion
            + self.cs_sales_admin_cost

            + self.cs_tax_portion

            + self.cs_logistics_costs
            + self.cs_warehouse_cost
            + self.cs_prod_indirect_labor
            + self.cs_prod_indirect_others
            + self.cs_direct_labor_costs
            + self.cs_depreciation_others
            + self.cs_profit
        )

        print("cs_sum", self.name, cs_sum)



    # ******************************
    # evaluation 
    # ******************************


    def set_lot_counts(self):

        plan_len = 53 * self.plan_range

        for w in range(0, plan_len):  ### 以下のi+1で1週スタート = W1,W2,W3,,
            self.lot_counts[w] = len(self.psi4supply[w][3])  # psi[w][3]=PO

        self.lot_counts_all = sum(self.lot_counts)





    def EvalPlanSIP_cost(self):

        L = self.lot_counts_all    # nodeの全ロット数 # psi[w][3]=PO
    
        # evaluated cost = Cost Structure X lot_counts
        self.eval_cs_price_sales_shipped    = L * self.cs_price_sales_shipped
        self.eval_cs_cost_total             = L * self.cs_cost_total
        self.eval_cs_profit                 = L * self.cs_profit
        self.eval_cs_marketing_promotion    = L * self.cs_marketing_promotion
        self.eval_cs_sales_admin_cost       = L * self.cs_sales_admin_cost
        self.eval_cs_SGA_total              = L * self.cs_SGA_total

        self.eval_cs_logistics_costs        = L * self.cs_logistics_costs
        self.eval_cs_warehouse_cost         = L * self.cs_warehouse_cost
        self.eval_cs_direct_materials_costs = L * self.cs_direct_materials_costs

        #self.eval_cs_custom_tax             = L * self.cs_custom_tax # STOP

        #@ RUN
        self.eval_cs_tax_portion            = L * self.cs_tax_portion


        #@STOP normalize_costで定義済み
        # ****************************
        # custom_tax = materials_cost imported X custom_tariff 
        # ****************************
        #self.eval_cs_tax_portion            = self.eval_cs_direct_materials_costs * self.customs_tariff_rate
        
    
        self.eval_cs_purchase_total_cost    = L * self.cs_purchase_total_cost
        self.eval_cs_prod_indirect_labor    = L * self.cs_prod_indirect_labor
        self.eval_cs_prod_indirect_others   = L * self.cs_prod_indirect_others
        self.eval_cs_direct_labor_costs     = L * self.cs_direct_labor_costs
        self.eval_cs_depreciation_others    = L * self.cs_depreciation_others
        self.eval_cs_manufacturing_overhead = L * self.cs_manufacturing_overhead    
    
        # 在庫係数の計算
        I_total_qty_planned, I_total_qty_init = self.I_lot_counts_all() 
    
        if I_total_qty_init == 0:

            I_cost_coeff = 0

        else:

            I_cost_coeff =  I_total_qty_planned / I_total_qty_init
    
        print("self.name",self.name)
        print("I_total_qty_planned", I_total_qty_planned)
        print("I_total_qty_init", I_total_qty_init)
        print("I_cost_coeff", I_cost_coeff)
    
        # 在庫の増減係数を掛けてセット

        print("self.eval_cs_warehouse_cost", self.eval_cs_warehouse_cost)

        self.eval_cs_warehouse_cost *= ( 1 + I_cost_coeff )

        print("self.eval_cs_warehouse_cost", self.eval_cs_warehouse_cost)

    
        self.eval_cs_cost_total = (

            self.eval_cs_marketing_promotion + 
            self.eval_cs_sales_admin_cost + 
            #self.eval_cs_SGA_total + 

            #self.eval_cs_custom_tax + 
            self.eval_cs_tax_portion + 

            self.eval_cs_logistics_costs + 
            self.eval_cs_warehouse_cost + 
            self.eval_cs_direct_materials_costs + 
            #self.eval_cs_purchase_total_cost + 

            self.eval_cs_prod_indirect_labor + 
            self.eval_cs_prod_indirect_others + 
            self.eval_cs_direct_labor_costs + 
            self.eval_cs_depreciation_others #@END + 
            #self.eval_cs_manufacturing_overhead
        )
    
        # profit = revenue - cost
        self.eval_cs_profit = self.eval_cs_price_sales_shipped - self.eval_cs_cost_total
    
        return self.eval_cs_price_sales_shipped, self.eval_cs_profit







    # *****************************
    # ここでCPU_LOTsを抽出する
    # *****************************
    def extract_CPU(self, csv_writer):

        plan_len = 53 * self.plan_range  # 計画長をセット

        # w=1から抽出処理

        # starting_I = 0 = w-1 / ending_I=plan_len
        for w in range(1, plan_len):

            # for w in range(1,54):   #starting_I = 0 = w-1 / ending_I = 53

            s = self.psi4supply[w][0]

            co = self.psi4supply[w][1]

            i0 = self.psi4supply[w - 1][2]
            i1 = self.psi4supply[w][2]

            p = self.psi4supply[w][3]

            # ***************************
            # write CPU
            # ***************************
            #
            # ISO_week_no,
            # CPU_lot_id,
            # S-I-P区分,
            # node座標(longitude, latitude),
            # step(高さ=何段目),
            # lot_size
            # ***************************

            # ***************************
            # write "s" CPU
            # ***************************
            for step_no, lot_id in enumerate(s):

                # lot_idを計画週YYYYWWでユニークにする
                lot_id_yyyyww = lot_id + str(self.plan_year_st) + str(w).zfill(4)

                CPU_row = [
                    w,
                    lot_id_yyyyww,
                    "s",
                    self.name,
                    self.longitude,
                    self.latitude,
                    step_no,
                    self.lot_size,
                ]

                csv_writer.writerow(CPU_row)

            # ***************************
            # write "i1" CPU
            # ***************************
            for step_no, lot_id in enumerate(i1):

                # lot_idを計画週YYYYWWでユニークにする
                lot_id_yyyyww = lot_id + str(self.plan_year_st) + str(w).zfill(4)

                CPU_row = [
                    w,
                    lot_id_yyyyww,
                    "i1",
                    self.name,
                    self.longitude,
                    self.latitude,
                    step_no,
                    self.lot_size,
                ]

                csv_writer.writerow(CPU_row)

            # ***************************
            # write "p" CPU
            # ***************************
            for step_no, lot_id in enumerate(p):

                # lot_idを計画週YYYYWWでユニークにする
                lot_id_yyyyww = lot_id + str(self.plan_year_st) + str(w).zfill(4)

                CPU_row = [
                    w,
                    lot_id_yyyyww,
                    "p",
                    self.name,
                    self.longitude,
                    self.latitude,
                    step_no,
                    self.lot_size,
                ]

                csv_writer.writerow(CPU_row)




    # ******************************
    # planning operation on tree
    # ******************************

    # ******************************
    # in or out    : root_node_outbound
    # plan layer   : demand layer
    # node order   : preorder # Leaf2Root
    # time         : Foreward
    # calculation  : PS2I
    # ******************************

    def calcPS2I4demand(self):

        # psiS2P = self.psi4demand # copyせずに、直接さわる

        plan_len = 53 * self.plan_range
        # plan_len = len(self.psi4demand)

        for w in range(1, plan_len):  # starting_I = 0 = w-1 / ending_I =plan_len
            # for w in range(1,54): # starting_I = 0 = w-1 / ending_I = 53

            s = self.psi4demand[w][0]
            co = self.psi4demand[w][1]

            i0 = self.psi4demand[w - 1][2]
            i1 = self.psi4demand[w][2]

            p = self.psi4demand[w][3]

            # *********************
            # # I(n-1)+P(n)-S(n)
            # *********************

            work = i0 + p  # 前週在庫と当週着荷分 availables

            # ここで、期末の在庫、S出荷=売上を操作している
            # S出荷=売上を明示的にlogにして、売上として記録し、表示する処理
            # 出荷されたS=売上、在庫I、未出荷COの集合を正しく表現する

            # モノがお金に代わる瞬間 #@240909コこではなくてS実績

            diff_list = [x for x in work if x not in s]  # I(n-1)+P(n)-S(n)

            self.psi4demand[w][2] = i1 = diff_list



    # *********************************
    # #@250626 TEST DATA DUMP4ALLOCATION
    # *********************************
    #@250626 TEST DATA DUMP4ALLOCATION
    def dump_PSI_psi4demand(self):
    
    # psiS2P = self.psi4demand # copyせずに、直接さわる

        print("dumpping node = ", self.name)
        
        plan_len = 53 * self.plan_range
        # plan_len = len(self.psi4demand)

        for w in range(1, plan_len):  # starting_I = 0 = w-1 / ending_I =plan_len
            s = self.psi4demand[w][0]
            co = self.psi4demand[w][1]

            i0 = self.psi4demand[w - 1][2]
            i1 = self.psi4demand[w][2]

            p = self.psi4demand[w][3]

            print("s = self.psi4demand[w][0]", w, s,"&[w][3]", p,"&[w][2]", i1)






    def calcPS2I4supply(self):

        # psiS2P = self.psi4demand # copyせずに、直接さわる

        plan_len = 53 * self.plan_range
        # plan_len = len(self.psi4supply)

        for w in range(1, plan_len):  # starting_I = 0 = w-1 / ending_I =plan_len
            # for w in range(1,54): # starting_I = 0 = w-1 / ending_I = 53

            s = self.psi4supply[w][0]
            co = self.psi4supply[w][1]

            i0 = self.psi4supply[w - 1][2]
            i1 = self.psi4supply[w][2]

            p = self.psi4supply[w][3]


            # *********************
            # # I(n-1)+P(n)-S(n)
            # *********************
            # memo ここで、期末の在庫、S出荷=売上を操作している
            # S出荷=売上を明示的にlogにして、売上として記録し、表示する処理
            # 出荷されたS=売上、在庫I、未出荷COの集合を正しく表現する
            #
            # モノがお金に代わる瞬間
            #

            #@250616 STOP
            #work = i0 + p  # 前週在庫と当週着荷分 availables
            #diff_list = [x for x in work if x not in s]  # I(n-1)+P(n)-S(n)


            def fifo_lot_diff(i0: list, p: list, s: list) -> list:
                work = i0 + p  # 順序保持
                result = []
                used = set()
            
                for lot in work:
                    if lot not in s and lot not in used:
                        result.append(lot)
                        used.add(lot)
                        
                return result

            diff_list = fifo_lot_diff(i0, p, s)


            self.psi4supply[w][2] = i1 = diff_list

            # ************************************
            # probare a lot checking process
            # ************************************
            
            if self.name == "DADCAL":

                #if w in [53,54,55,56,57]:
                if w < 58 :

                    print("s, co, i0, i1, p ", w )
                    print("s" , w, s )
                    print("co", w, co)
                    print("i0", w, i0)
                    print("i1", w, i1)
                    print("p" , w, p )


    def calcPS2I_decouple4supply(self):

        # psiS2P = self.psi4demand # copyせずに、直接さわる

        plan_len = 53 * self.plan_range
        # plan_len = len(self.psi4supply)

        # demand planのSを出荷指示情報=PULL SIGNALとして、supply planSにセット

        for w in range(0, plan_len):
            # for w in range(1,plan_len):

            # pointer参照していないか? 明示的にデータを渡すには?

            self.psi4supply[w][0] = self.psi4demand[w][
                0
            ].copy()  # copy data using copy() method

            # self.psi4supply[w][0]    = self.psi4demand[w][0] # PULL replaced

            # checking pull data
            # show_psi_graph(root_node_outbound,"supply", "HAM", 0, 300 )
            # show_psi_graph(root_node_outbound,"supply", node_show, 0, 300 )

        for w in range(1, plan_len):  # starting_I = 0 = w-1 / ending_I =plan_len

            # demand planSをsupplySにコピー済み
            s = self.psi4supply[w][0]  # PUSH supply S

            co = self.psi4supply[w][1]

            i0 = self.psi4supply[w - 1][2]
            i1 = self.psi4supply[w][2]

            p = self.psi4supply[w][3]

            # *********************
            # # I(n-1)+P(n)-S(n)
            # *********************

            work = i0 + p  # 前週在庫と当週着荷分 availables

            # memo ここで、期末の在庫、S出荷=売上を操作している
            # S出荷=売上を明示的にlogにして、売上として記録し、表示する処理
            # 出荷されたS=売上、在庫I、未出荷COの集合を正しく表現する

            # モノがお金に代わる瞬間

            diff_list = [x for x in work if x not in s]  # I(n-1)+P(n)-S(n)

            self.psi4supply[w][2] = i1 = diff_list




    def calcS2P(self): # backward planning

        # **************************
        # Safety Stock as LT shift
        # **************************
        # leadtimeとsafety_stock_weekは、ここでは同じ

        # 同一node内なので、ssのみで良い
        shift_week = int(round(self.SS_days / 7))

        ## stop 同一node内でのLT shiftは無し
        ## SS is rounded_int_num
        # shift_week = self.leadtime +  int(round(self.SS_days / 7))

        # **************************
        # long vacation weeks
        # **************************
        lv_week = self.long_vacation_weeks

        # 同じnode内でのS to P の計算処理 # backward planning
        self.psi4demand = shiftS2P_LV(self.psi4demand, shift_week, lv_week)

        pass




    def calcS2P_4supply(self):    # "self.psi4supply"
        # **************************
        # Safety Stock as LT shift
        # **************************
        # leadtimeとsafety_stock_weekは、ここでは同じ

        # 同一node内なので、ssのみで良い
        shift_week = int(round(self.SS_days / 7))

        ## stop 同一node内でのLT shiftは無し
        ## SS is rounded_int_num
        # shift_week = self.leadtime +  int(round(self.SS_days / 7))

        # **************************
        # long vacation weeks
        # **************************
        lv_week = self.long_vacation_weeks

        # S to P の計算処理
        self.psi4supply = shiftS2P_LV_replace(self.psi4supply, shift_week, lv_week)

        pass




    def set_plan_range_lot_counts(self, plan_range, plan_year_st):

        # print("node.plan_range", self.name, self.plan_range)

        self.plan_range = plan_range
        self.plan_year_st = plan_year_st

        self.lot_counts = [0 for x in range(0, 53 * self.plan_range)]


        for child in self.children:

            child.set_plan_range_lot_counts(plan_range, plan_year_st)





    def I_lot_counts_all(self):
        lot_all_supply = 0
        lot_all_demand = 0

        plan_len = 53 * self.plan_range

        lot_counts_I_supply = [0] * plan_len
        lot_counts_I_demand = [0] * plan_len

        #@241129 DEBUG DUMP TEST self.psi4supply
        #if self.name == "HAM":
        #    print("self.psi4supply",self.psi4supply)




        for w in range(plan_len):  ### 以下のi+1で1週スタート = W1,W2,W3,,
            lot_counts_I_supply[w] = len(self.psi4supply[w][2])  # psi[w][2]=I
            lot_counts_I_demand[w] = len(self.psi4demand[w][2])  # psi[w][2]=I


        #@241129 DUMP TEST self.psi4supply
        if self.name == "HAM":
            print("lot_counts_I_supply",lot_counts_I_supply)



        lot_all_supply = sum(lot_counts_I_supply)
        lot_all_demand = sum(lot_counts_I_demand)

        return lot_all_supply, lot_all_demand


# *********************************
#@250511 added for PlanningEngine
# *********************************
    def eval_buffer_stock_OLD(self):
        """
        各週の在庫量が安全在庫週数に基づく閾値を下回っていないかを評価する。
        条件に満たない場合は警告表示や補正処理を行う。
        """
        if self.psi4supply is None or len(self.psi4supply) == 0:
            print(f"[Warning] {self.name}: No supply PSI data available.")
            return
    
        threshold_weeks = self.safety_stock_week if self.safety_stock_week > 0 else self.leadtime
        safe_threshold = threshold_weeks * self.nx_demand  # 週×1週間あたり需要量

        for w, week_data in enumerate(self.psi4supply):
            if len(week_data) < 3:
                continue  # I在庫が不足していればスキップ
            inventory_level = week_data[2]  # I(n) = psi4supply[n][2]
            total_qty = sum(inventory_level) if isinstance(inventory_level, list) else inventory_level
            if total_qty < safe_threshold:
                print(f"[BufferStock Alert] {self.name} - Week {w}: Inventory {total_qty} < Safe {safe_threshold}")


    def eval_buffer_stock(self):
        """
        PSI情報をもとに、在庫水準（I）、未出荷（CO）、生産（P）ロット数の異常を評価。
        評価結果はログ出力される。
        """
        if self.psi4supply is None or len(self.psi4supply) == 0:
            print(f"[Warning] {self.name}: No supply PSI data available.")
            return

        threshold_weeks = self.safety_stock_week if self.safety_stock_week > 0 else self.leadtime
        safe_threshold = threshold_weeks * self.nx_demand

        co_threshold = self.nx_demand * 2  # 未出荷ロットの目安
        p_max_threshold = self.nx_capacity  # 許容量超えた生産負荷

        for w, week_data in enumerate(self.psi4supply):
            if len(week_data) < 4:
                continue

            # 在庫評価
            inventory = week_data[2]
            inventory_qty = sum(inventory) if isinstance(inventory, list) else inventory
            if inventory_qty < safe_threshold:
                print(f"[Stock Alert] {self.name} - W{w}: Inventory {inventory_qty} < Safe {safe_threshold}")

            # CO評価
            co = week_data[1]
            co_qty = sum(co) if isinstance(co, list) else co
            if co_qty > co_threshold:
                print(f"[CO Alert] {self.name} - W{w}: CarryOver {co_qty} > Limit {co_threshold}")

            # P評価
            p = week_data[3]
            p_qty = len(p) if isinstance(p, list) else p
            if p_qty > p_max_threshold:
                print(f"[Production Alert] {self.name} - W{w}: Production {p_qty} > Capacity {p_max_threshold}")



    def optimize_network_OLD(self):
        """
        ネットワーク最適化処理（例: 利益を改善するためのリードタイム・容量調整の提案）。
        将来的にORモデルやMLと連携可能な設計に。
        """

        # 利益がマイナスなら、容量・価格設定の調整案を提案
        if self.eval_cs_profit < 0:
            print(f"[Optimize] {self.name} is in deficit. Considering improvements...")

            # 仮の調整案：容量を増やす or 販売価格を引き上げる
            if self.nx_capacity < 5:
                self.nx_capacity += 1
                print(f" - Increased capacity to {self.nx_capacity}")

            # 利益率を引き上げた場合のシミュレーション（簡易）
            improvement_ratio = 1.1
            self.eval_cs_price_sales_shipped *= improvement_ratio
            self.eval_cs_profit = self.eval_cs_price_sales_shipped - self.eval_cs_cost_total
            print(f" - Simulated price increase. New profit: {self.eval_cs_profit:.2f}")


    def optimize_network(self):
        """
        ネットワーク最適化処理：
        赤字の場合や特定コスト項目が過大な場合に、改善案を提示する。
        """

        print(f"[Optimize] {self.name} evaluating cost structure...")

        # 基準閾値（例：%として定義）
        max_sga_ratio = 0.2
        max_logistics_ratio = 0.15
        max_warehouse_ratio = 0.10
        max_tax_ratio = 0.05

        # コスト合計と各項目を抽出
        total_cost = self.eval_cs_cost_total
        if total_cost == 0:
            print(f" - {self.name}: Skipped (no cost data)")
            return

        alerts = []

        # 各コスト比率を評価
        sga = self.eval_cs_SGA_total / total_cost
        if sga > max_sga_ratio:
            alerts.append(f"SG&A比率高: {sga:.2%} > {max_sga_ratio:.0%}")
            self.eval_cs_SGA_total *= 0.9  # 10%削減シミュレーション

        logistics = self.eval_cs_logistics_costs / total_cost
        if logistics > max_logistics_ratio:
            alerts.append(f"物流費高: {logistics:.2%} > {max_logistics_ratio:.0%}")
            self.eval_cs_logistics_costs *= 0.9

        wh = self.eval_cs_warehouse_cost / total_cost
        if wh > max_warehouse_ratio:
            alerts.append(f"倉庫費高: {wh:.2%} > {max_warehouse_ratio:.0%}")
            self.eval_cs_warehouse_cost *= 0.9

        tax = self.eval_cs_tax_portion / total_cost
        if tax > max_tax_ratio:
            alerts.append(f"税金高: {tax:.2%} > {max_tax_ratio:.0%}")
            self.eval_cs_tax_portion *= 0.95

        if alerts:
            print(f" - {self.name} コスト最適化対象:\n   " + "\n   ".join(alerts))
            # 再計算（簡易）
            self.eval_cs_cost_total = (
                self.eval_cs_SGA_total + self.eval_cs_logistics_costs +
                self.eval_cs_warehouse_cost + self.eval_cs_tax_portion +
                self.eval_cs_direct_materials_costs +
                self.eval_cs_prod_indirect_labor + self.eval_cs_prod_indirect_others +
                self.eval_cs_direct_labor_costs + self.eval_cs_depreciation_others
            )
            self.eval_cs_profit = self.eval_cs_price_sales_shipped - self.eval_cs_cost_total
            print(f"   => 改善後利益: {self.eval_cs_profit:.2f}")
        else:
            print(f" - {self.name}: コスト構成は良好です。")




# *************************
# class SKU
# *************************

class SKU:
    def __init__(self, product_name, node_name):
        self.product_name = product_name
        self.node_name = node_name

        self.psi_table = defaultdict(lambda: {"I": 0, "P": 0, "S": 0, "CO": 0})  # week単位



        # *******************
        # move Node 2 SKU
        # *******************
        self.lot_size = 1  # default setting
        self.psi = []  # Placeholder for PSI data

        self.iso_week_demand = None  # Original demand converted to ISO week
        self.psi4demand = None
        self.psi4supply = None
        self.psi4couple = None
        self.psi4accume = None

        self.plan_range = 1
        self.plan_year_st = 2025

        self.safety_stock_week = 0
        self.long_vacation_weeks = []



        # For NetworkX
        self.leadtime = 1   # same as safety_stock_week
        self.nx_demand = 1  # weekly average demand by lot
        self.nx_weight = 1  # move_cost_all_to_nodeB (from nodeA to nodeB)
        self.nx_capacity = 1  # lot by lot


        # Evaluation
        self.decoupling_total_I = []  # total Inventory all over the plan


        # "lot_counts" is the bridge PSI2EVAL
        self.lot_counts = [0 for x in range(0, 53 * self.plan_range)]
        self.lot_counts_all = 0  # sum(self.lot_counts)

        # Settings for cost-profit evaluation parameter
        self.LT_boat = 1
        self.SS_days = 7
        self.HS_code = ""
        self.customs_tariff_rate = 0
        self.tariff_on_price = 0
        self.price_elasticity = 0




        # ******************************
        # evaluation data initialise rewardsを計算の初期化
        # ******************************

        # ******************************
        # Profit_Ratio #float
        # ******************************
        self.eval_profit_ratio = Profit_Ratio = 0.6

        # Revenue, Profit and Costs
        self.eval_revenue = 0
        self.eval_profit = 0


        self.eval_PO_cost = 0
        self.eval_P_cost = 0
        self.eval_WH_cost = 0
        self.eval_SGMC = 0
        self.eval_Dist_Cost = 0



        # ******************************
        # set_EVAL_cash_in_data #list for 53weeks * 5 years # 5年を想定
        # *******************************
        self.Profit = Profit = [0 for i in range(53 * self.plan_range)]
        self.Week_Intrest = Week_Intrest = [0 for i in range(53 * self.plan_range)]
        self.Cash_In = Cash_In = [0 for i in range(53 * self.plan_range)]
        self.Shipped_LOT = Shipped_LOT = [0 for i in range(53 * self.plan_range)]
        self.Shipped = Shipped = [0 for i in range(53 * self.plan_range)]

        # ******************************
        # set_EVAL_cash_out_data #list for 54 weeks
        # ******************************

        self.SGMC = SGMC = [0 for i in range(53 * self.plan_range)]
        self.PO_manage = PO_manage = [0 for i in range(53 * self.plan_range)]
        self.PO_cost = PO_cost = [0 for i in range(53 * self.plan_range)]
        self.P_unit = P_unit = [0 for i in range(53 * self.plan_range)]
        self.P_cost = P_cost = [0 for i in range(53 * self.plan_range)]

        self.I = I = [0 for i in range(53 * self.plan_range)]

        self.I_unit = I_unit = [0 for i in range(53 * self.plan_range)]
        self.WH_cost = WH_cost = [0 for i in range(53 * self.plan_range)]
        self.Dist_Cost = Dist_Cost = [0 for i in range(53 * self.plan_range)]



        # Cost structure demand
        self.price_sales_shipped = 0
        self.cost_total = 0
        self.profit = 0
        self.marketing_promotion = 0
        self.sales_admin_cost = 0
        self.SGA_total = 0
        self.custom_tax = 0
        self.tax_portion = 0
        self.logistics_costs = 0
        self.warehouse_cost = 0
        self.direct_materials_costs = 0
        self.purchase_total_cost = 0
        self.prod_indirect_labor = 0
        self.prod_indirect_others = 0
        self.direct_labor_costs = 0
        self.depreciation_others = 0
        self.manufacturing_overhead = 0

        # Profit accumulated root to node
        self.cs_profit_accume = 0

        # Cost Structure
        self.cs_price_sales_shipped = 0
        self.cs_cost_total = 0
        self.cs_profit = 0
        self.cs_marketing_promotion = 0
        self.cs_sales_admin_cost = 0
        self.cs_SGA_total = 0

        #self.cs_custom_tax = 0 # stop tariff_rate

        self.cs_tax_portion = 0
        self.cs_logistics_costs = 0
        self.cs_warehouse_cost = 0
        self.cs_direct_materials_costs = 0
        self.cs_purchase_total_cost = 0
        self.cs_prod_indirect_labor = 0
        self.cs_prod_indirect_others = 0
        self.cs_direct_labor_costs = 0
        self.cs_depreciation_others = 0
        self.cs_manufacturing_overhead = 0

        # Evaluated cost = Cost Structure X lot_counts
        self.eval_cs_price_sales_shipped = 0  # revenue
        self.eval_cs_cost_total = 0  # cost
        self.eval_cs_profit = 0  # profit
        self.eval_cs_marketing_promotion = 0
        self.eval_cs_sales_admin_cost = 0
        self.eval_cs_SGA_total = 0

        #self.eval_cs_custom_tax = 0 # stop tariff rate

        self.eval_cs_tax_portion = 0
        self.eval_cs_logistics_costs = 0
        self.eval_cs_warehouse_cost = 0
        self.eval_cs_direct_materials_costs = 0
        self.eval_cs_purchase_total_cost = 0
        self.eval_cs_prod_indirect_labor = 0
        self.eval_cs_prod_indirect_others = 0
        self.eval_cs_direct_labor_costs = 0
        self.eval_cs_depreciation_others = 0
        self.eval_cs_manufacturing_overhead = 0

        # Shipped lots count W / M / Q / Y / LifeCycle
        self.shipped_lots_W = []  # 53*plan_range
        self.shipped_lots_M = []  # 12*plan_range
        self.shipped_lots_Q = []  # 4*plan_range
        self.shipped_lots_Y = []  # 1*plan_range
        self.shipped_lots_L = []  # 1  # lifecycle a year

        # Planned Amount
        self.amt_price_sales_shipped = []    # Revenue cash_IN???
        self.amt_cost_total = []
        self.amt_profit = []                 # Profit
        self.amt_marketing_promotion = []
        self.amt_sales_admin_cost = []
        self.amt_SGA_total = []
        self.amt_custom_tax = []
        self.amt_tax_portion = []
        self.amt_logistiamt_costs = []
        self.amt_warehouse_cost = []
        self.amt_direct_materials_costs = [] # FOB@port 
        self.amt_purchase_total_cost = []    # 
        self.amt_prod_indirect_labor = []
        self.amt_prod_indirect_others = []
        self.amt_direct_labor_costs = []
        self.amt_depreciation_others = []
        self.amt_manufacturing_overhead = []

        # Shipped amt W / M / Q / Y / LifeCycle
        self.shipped_amt_W = []  # 53*plan_range
        self.shipped_amt_M = []  # 12*plan_range
        self.shipped_amt_Q = []  # 4*plan_range
        self.shipped_amt_Y = []  # 1*plan_range
        self.shipped_amt_L = []  # 1  # lifecycle a year

        # Control FLAGs
        self.cost_standard_flag = 0
        self.PSI_graph_flag = "OFF"
        self.buffering_stock_flag = "OFF"

        self.revenue = 0
        self.profit  = 0

        self.AR_lead_time = 0 # Accounts Receivable 売掛
        self.AP_lead_time = 0 # Accounts Payable 買掛






# ****************************
# after demand leveling / planning outbound supply
# ****************************
def shiftS2P_LV_replace(psiS, shift_week, lv_week):  # LV:long vacations

    # ss = safety_stock_week
    sw = shift_week

    plan_len = len(psiS) - 1  # -1 for week list position

    for w in range(plan_len):  # foreward planningでsupplyのp [w][3]を初期化

        # psiS[w][0] = [] # S active

        psiS[w][1] = []  # CO
        psiS[w][2] = []  # I
        psiS[w][3] = []  # P

    for w in range(plan_len, sw, -1):  # backward planningでsupplyを降順でシフト

        # my_list = [1, 2, 3, 4, 5]
        # for i in range(2, len(my_list)):
        #    my_list[i] = my_list[i-1] + my_list[i-2]

        # 0:S
        # 1:CO
        # 2:I
        # 3:P

        eta_plan = w - sw  # sw:shift week ( including safty stock )

        eta_shift = check_lv_week_bw(lv_week, eta_plan)  # ETA:Eatimate Time Arrival

        # リスト追加 extend
        # 安全在庫とカレンダ制約を考慮した着荷予定週Pに、w週Sからoffsetする
        psiS[eta_shift][3].extend(psiS[w][0])  # P made by shifting S with

    return psiS




# ****************************
# PSI planning demand
# ****************************
def calc_all_psi2i4demand(node):

    node.calcPS2I4demand()

    for child in node.children:

        calc_all_psi2i4demand(child)




# ****************************
# connect_out2in
# ****************************




def connect_out2in_dict_copy(node_psi_dict_Ot4Dm, node_psi_dict_In4Dm):

    node_psi_dict_In4Dm = node_psi_dict_Ot4Dm.copy()
    
    return node_psi_dict_In4Dm




def psi_dict_copy(from_psi_dict, to_psi_dict):

    to_psi_dict = from_psi_dict.copy()
    
    return to_psi_dict






def connect_out2in_psi_copy(root_node_outbound, root_node_inbound):

    # ***************************************
    # setting root node OUTBOUND to INBOUND
    # ***************************************

    plan_range = root_node_outbound.plan_range

    root_node_inbound.psi4demand = root_node_outbound.psi4supply.copy()




def connect_outbound2inbound(root_node_outbound, root_node_inbound):

    # ***************************************
    # setting root node OUTBOUND to INBOUND
    # ***************************************

    plan_range = root_node_outbound.plan_range

    for w in range(53 * plan_range):

        root_node_inbound.psi4demand[w][0] = root_node_outbound.psi4supply[w][0].copy()
        root_node_inbound.psi4demand[w][1] = root_node_outbound.psi4supply[w][1].copy()
        root_node_inbound.psi4demand[w][2] = root_node_outbound.psi4supply[w][2].copy()
        root_node_inbound.psi4demand[w][3] = root_node_outbound.psi4supply[w][3].copy()

        root_node_inbound.psi4supply[w][0] = root_node_outbound.psi4supply[w][0].copy()
        root_node_inbound.psi4supply[w][1] = root_node_outbound.psi4supply[w][1].copy()
        root_node_inbound.psi4supply[w][2] = root_node_outbound.psi4supply[w][2].copy()
        root_node_inbound.psi4supply[w][3] = root_node_outbound.psi4supply[w][3].copy()





# ************************************
# checking constraint to inactive week , that is "Long Vacation"
# ************************************
def check_lv_week_bw(const_lst, check_week):

    num = check_week

    if const_lst == []:

        pass

    else:

        while num in const_lst:

            num -= 1

    return num




def shift_P2childS_LV(node, child, safety_stock_week, lv_week):

    # psiP = node.psi4demand

    ss = safety_stock_week

    plan_len = len(node.psi4demand) - 1  # -1 for week list position
    #plan_len = len(psiP) - 1  # -1 for week list position

    for w in range( (plan_len - 1), 0, -1):  # forward planningで確定Pを確定Sにシフト

        # my_list = [1, 2, 3, 4, 5]
        # for i in range(2, len(my_list)):
        #    my_list[i] = my_list[i-1] + my_list[i-2]

        # 0:S
        # 1:CO
        # 2:I
        # 3:P

        etd_plan = w - ss  # ss:safty stock

        etd_shift = check_lv_week_bw(lv_week,etd_plan) #BW ETD:Eatimate TimeDep
        # リスト追加 extend
        # 安全在庫とカレンダ制約を考慮した着荷予定週Pに、w週Sからoffsetする

        # "child S" position made by shifting P with

        #child.psi4supply[etd_shift][0] = node.psi4supply[w][3]

        print("[etd_shift][0] [w][3]  ",child.name,etd_shift, "  ",node.name,w)

        if etd_shift > 0:

            child.psi4demand[etd_shift][0] = node.psi4demand[w][3]

        else:

            pass

        #psi[etd_shift][0] = psiP[w][3]  # S made by shifting P with

    #return psiP
    #
    #return psi



def check_lv_week_fw(const_lst, check_week):

    num = check_week

    if const_lst == []:

        pass

    else:

        while num in const_lst:

            num += 1

    return num




# backward P2S ETD_shifting 
def shiftP2S_LV(psiP, safety_stock_week, lv_week):  # LV:long vacations

    ss = safety_stock_week

    plan_len = len(psiP) - 1  # -1 for week list position

    for w in range(plan_len - 1):  # forward planningで確定Pを確定Sにシフト

        # my_list = [1, 2, 3, 4, 5]
        # for i in range(2, len(my_list)):
        #    my_list[i] = my_list[i-1] + my_list[i-2]

        # 0:S
        # 1:CO
        # 2:I
        # 3:P

        etd_plan = w + ss  # ss:safty stock

        etd_shift = check_lv_week_fw(lv_week, etd_plan)  # ETD:Eatimate TimeDep
        # リスト追加 extend
        # 安全在庫とカレンダ制約を考慮した着荷予定週Pに、w週Sからoffsetする

        psiP[etd_shift][0] = psiP[w][3]  # S made by shifting P with

    return psiP


# P2S
def calc_all_psiS2P2childS_preorder(node):

    # inbound supply backward plan with pre_ordering
    #node.calcS2P_4supply()    # "self.psi4supply"

    # nodeの中で、S2P
    node.calcS2P()    # "self.psi4demand" # backward planning

    if node.children == []:

        pass

    else:

        for child in node.children:

    #def calc_all_P2S(node)
            # **************************
            # Safety Stock as LT shift
            # **************************
            safety_stock_week = child.leadtime

            # **************************
            # long vacation weeks
            # **************************
            lv_week = child.long_vacation_weeks

            # P to S の計算処理
            # backward P2S ETD_shifting 
            #self.psi4supply = shiftP2S_LV(node.psi4supply, safety_stock_week, lv_week)

            # node, childのpsi4supplyを直接update
            shift_P2childS_LV(node, child, safety_stock_week, lv_week)

            #child.psi4supply = shift_P2childS_LV(node, child, safety_stock_week, lv_week)


    for child in node.children:

        calc_all_psiS2P2childS_preorder(child)





def calc_all_psi2i4supply_post(node):



    for child in node.children:

        calc_all_psi2i4supply_post(child)

    node.calcPS2I4supply()




# ****************************
# Inbound Demand Backward Plan
# ****************************
#  class NodeのメソッドcalcS2Pと同じだが、node_psiの辞書を更新してreturn
def calc_bwd_inbound_si2p(node, node_psi_dict_In4Dm):

    # **************************
    # Safety Stock as LT shift
    # **************************
    # leadtimeとsafety_stock_weekは、ここでは同じ

    #@240906 SS+LTでoffset

    safety_stock_week = int(round(node.SS_days / 7))

    #safety_stock_week += node.leadtime

    # **************************
    # long vacation weeks
    # **************************
    lv_week = node.long_vacation_weeks

    # S to P の計算処理  # dictに入れればself.psi4supplyから接続して見える
    node_psi_dict_In4Dm[node.name] = shiftS2P_LV(
        node.psi4demand, safety_stock_week, lv_week
    )

    return node_psi_dict_In4Dm


def calc_bwd_inbound_all_si2p(node, node_psi_dict_In4Dm):

    plan_range = node.plan_range

    # ********************************
    # inboundは、親nodeのSをそのままPに、shift S2Pして、node_spi_dictを更新
    # ********************************
    #    S2P # dictにlistセット
    node_psi_dict_In4Dm = calc_bwd_inbound_si2p(node, node_psi_dict_In4Dm)

    # *********************************
    # 子nodeがあればP2_child.S
    # *********************************

    if node.children == []:

        pass

    else:

        # inboundの場合には、dict=[]でセット済　代入する[]になる
        # 辞書のgetメソッドでキーnameから値listを取得。
        # キーが存在しない場合はNone
        # self.psi4demand = node_psi_dict_In4Dm.get(self.name)

        for child in node.children:

            for w in range(53 * plan_range):

                # move_lot P2S
                child.psi4demand[w][0] = node.psi4demand[w][3].copy()

    for child in node.children:

        calc_bwd_inbound_all_si2p(child, node_psi_dict_In4Dm)

    # stop 返さなくても、self.psi4demand[w][3]でPを参照できる。
    return node_psi_dict_In4Dm















# ****************************
# tree positioing
# ****************************
def set_positions_recursive(node, width_tracker):
    for child in node.children:
        child.depth = node.depth + 1
        child.width = width_tracker[child.depth]
        width_tracker[child.depth] += 1
        set_positions_recursive(child, width_tracker)

def adjust_positions(node):
    if not node.children:
        return node.width

    children_y_min = min(adjust_positions(child) for child in node.children)
    children_y_max = max(adjust_positions(child) for child in node.children)
    node.width = (children_y_min + children_y_max) / 2

    for i, child in enumerate(node.children):
        child.width += i * 0.1

    return node.width

def set_positions(root):
    width_tracker = [0] * 100
    set_positions_recursive(root, width_tracker)
    adjust_positions(root)




def set_node_costs(cost_table, nodes):
    """
    Set cost attributes for nodes based on the given cost table.

    Parameters:
        cost_table (pd.DataFrame): DataFrame containing cost data.
        nodes (dict): Dictionary of node instances.

    Returns:
        None
    """
    df_transposed = cost_table.transpose()

    rows = df_transposed.iterrows()
    next(rows)  # Skip the header row

    for index, row in rows:
        node_name = index
        try:
            node = nodes[node_name]
            node.set_cost_attr(*row)

            node.normalize_cost() # add Custom_Tax and normalize

            node.print_cost_attr()
        except KeyError:
            print(f"Warning: {node_name} not found in nodes. Continuing with next item.")




def set_parent_all(node):
    # preordering

    if node.children == []:
        pass
    else:
        node.set_parent()  # この中で子nodeを見て親を教える。
        # def set_parent(self)

    for child in node.children:

        set_parent_all(child)




def print_parent_all(node):
    # preordering

    if node.children == []:
        pass
    else:
        print("node.parent and children", node.name, node.children)

    for child in node.children:

        print("child and parent", child.name, node.name)

        print_parent_all(child)





def build_tree_from_dict(tree_dict: Dict[str, List[str]]) -> Node:
    """
    Build a tree structure from a dictionary.

    Parameters:
        tree_dict (Dict[str, List[str]]): A dictionary where keys are parent node names
                                         and values are lists of child node names.

    Returns:
        Node: The root node of the constructed tree.
    """
    nodes: Dict[str, Node] = {}

    # Create all nodes
    for parent, children in tree_dict.items():
        if parent not in nodes:
            nodes[parent] = Node(parent)
        for child in children:
            if child not in nodes:
                nodes[child] = Node(child)

    # Link nodes
    for parent, children in tree_dict.items():
        for child in children:
            nodes[parent].add_child(nodes[child])

    # Assume the root is the one without a parent
    root_candidates = set(nodes.keys()) - {child for children in tree_dict.values() for child in children}
    if len(root_candidates) != 1:
        raise ValueError("Tree must have exactly one root")

    root_name = root_candidates.pop()
    root = nodes[root_name]
    root.set_depth(0)
    return root



def create_tree_set_attribute(file_name):
    """
    Create a supply chain tree and set attributes, supporting multiple SKU per node.

    Parameters:
        file_name (str): Path to the tree file.

    Returns:
        tuple[dict, str]: Dictionary of Node instances and the root node name.
    """
    from collections import defaultdict

    width_tracker = defaultdict(int)
    root_node_name = ""

    rows = read_tree_file(file_name)
    nodes = {}

    # Phase 1: Create all nodes
    for row in rows:
        child_name = row["Child_node"]
        parent_name = row["Parent_node"]

        if child_name not in nodes:
            nodes[child_name] = Node(child_name)

        if parent_name != "root" and parent_name not in nodes:
            nodes[parent_name] = Node(parent_name)

    # Phase 2: Link tree structure
    for row in rows:
        parent_name = row["Parent_node"]
        child_name = row["Child_node"]
        if parent_name == "root":
            root_node_name = child_name
            nodes[root_node_name].width += 4
        else:
            parent = nodes[parent_name]
            child = nodes[child_name]
            parent.add_child(child)
            child.set_attributes(row)

    # Phase 3: Register SKUs (multiple SKUs per Node)
    for row in rows:
        child_name = row["Child_node"]
        if "product_name" in row and row["product_name"]:
            nodes[child_name].add_sku(row["product_name"])

    return nodes, root_node_name







# ******************************
# Evaluation process
# ******************************

def set_price_leaf2root(node, root_node_outbound, val):

    #print("node.name ", node.name)
    root_price = 0

    pb = 0
    pb = node.price_sales_shipped  # pb : Price_Base

    # set value on shipping price
    node.cs_price_sales_shipped = val

    print("def set_price_leaf2root", node.name, node.cs_price_sales_shipped )

    node.show_sum_cs()



    # cs : Cost_Stracrure
    node.cs_cost_total = val * node.cost_total / pb
    node.cs_profit = val * node.profit / pb
    node.cs_marketing_promotion = val * node.marketing_promotion / pb
    node.cs_sales_admin_cost = val * node.sales_admin_cost / pb
    node.cs_SGA_total = val * node.SGA_total / pb

    #node.cs_custom_tax = val * node.custom_tax / pb
    #node.cs_tax_portion = val * node.tax_portion / pb

    node.cs_logistics_costs = val * node.logistics_costs / pb
    node.cs_warehouse_cost = val * node.warehouse_cost / pb

    # direct shipping price that is,  like a FOB at port
    node.cs_direct_materials_costs = val * node.direct_materials_costs / pb

    node.cs_purchase_total_cost = val * node.purchase_total_cost / pb
    node.cs_prod_indirect_labor = val * node.prod_indirect_labor / pb
    node.cs_prod_indirect_others = val * node.prod_indirect_others / pb
    node.cs_direct_labor_costs = val * node.direct_labor_costs / pb
    node.cs_depreciation_others = val * node.depreciation_others / pb
    node.cs_manufacturing_overhead = val * node.manufacturing_overhead / pb

    print("probe")
    node.show_sum_cs()

    #print("node.cs_direct_materials_costs", node.name, node.cs_direct_materials_costs)
    #print("root_node_outbound.name", root_node_outbound.name)


    if node.name == root_node_outbound.name:
    #if node == root_node_outbound:

        node.cs_profit_accume = node.cs_profit # profit_accumeの初期セット

        root_price = node.cs_price_sales_shipped
        # root_price = node.cs_direct_materials_costs

        pass

    else:

        root_price = set_price_leaf2root(
            node.parent, root_node_outbound, node.cs_direct_materials_costs
        )

    return root_price




# 1st val is "root_price"
# 元の売値=valが、先の仕入れ値=pb Price_Base portionになる。
def set_value_chain_outbound(val, node):


    # root_nodeをpassして、子供からstart


    # はじめは、root_nodeなのでnode.childrenは存在する
    for child in node.children:

        #print("set_value_chain_outbound child.name ", child.name)
        # root_price = 0

        pb = 0
        pb = child.direct_materials_costs  # pb : Price_Base portion

        print("child.name", child.name)
        print("pb = child.direct_materials_costs",child.direct_materials_costs)

        # pb = child.price_sales_shipped # pb : Price_Base portion

        # direct shipping price that is,  like a FOB at port

        child.cs_direct_materials_costs = val

        ## direct shipping price that is,  like a FOB at port
        #node.cs_direct_materials_costs = val * node.direct_materials_costs /pb

        #@250322 updated
        #child.cs_custom_tax = val * child.custom_tax / pb   # STOP tariff_rate
        #child.cs_tax_portion = val * child.tax_portion / pb # custom_tax
        # ****************************
        # custom_tax = materials_cost imported X custom_tariff 
        # ****************************
        child.cs_tax_portion            = child.cs_direct_materials_costs * child.customs_tariff_rate



        # set value on shipping price
        child.cs_price_sales_shipped = val * child.price_sales_shipped / pb
        #print("def set_value_chain_outbound", child.name, child.cs_price_sales_shipped )
        child.show_sum_cs()



        val_child = child.cs_price_sales_shipped

        # cs : Cost_Stracrure
        child.cs_cost_total = val * child.cost_total / pb

        child.cs_profit = val * child.profit / pb

        # root2leafまでprofit_accume
        child.cs_profit_accume += node.cs_profit

        child.cs_marketing_promotion = val * child.marketing_promotion / pb
        child.cs_sales_admin_cost = val * child.sales_admin_cost / pb
        child.cs_SGA_total = val * child.SGA_total / pb

        child.cs_logistics_costs = val * child.logistics_costs / pb
        child.cs_warehouse_cost = val * child.warehouse_cost / pb


        child.cs_purchase_total_cost = val * child.purchase_total_cost / pb
        child.cs_prod_indirect_labor = val * child.prod_indirect_labor / pb
        child.cs_prod_indirect_others = val * child.prod_indirect_others / pb
        child.cs_direct_labor_costs = val * child.direct_labor_costs / pb
        child.cs_depreciation_others = val * child.depreciation_others / pb
        child.cs_manufacturing_overhead = val * child.manufacturing_overhead / pb

        #print("probe")
        #child.show_sum_cs()


        print(
            "node.cs_direct_materials_costs",
            child.name,
            child.cs_direct_materials_costs,
        )
        # print("root_node_outbound.name", root_node_outbound.name )

        # to be rewritten@240803

        if child.children == []:  # leaf_nodeなら終了

            pass

        else:  # 孫を処理する

            set_value_chain_outbound(val_child, child)

    # return


# **************************************
# call from gui.app
# **************************************




#@ STOP
#def eval_supply_chain_cost(node, context):
#    """
#    Recursively evaluates the cost of the entire supply chain.
#    
#    Parameters:
#        node (Node): The node currently being evaluated.
#        context (object): An object holding the total cost values (e.g., an instance of the GUI class).
#    """
#    # Count the number of lots for each node
#    node.set_lot_counts()
#
#    # Perform cost evaluation
#    total_revenue, total_profit = node.EvalPlanSIP_cost()
#
#    # Add the evaluation results to the context
#    context.total_revenue += total_revenue
#    context.total_profit += total_profit
#
#    # Recursively evaluate for child nodes
#    for child in node.children:
#        eval_supply_chain_cost(child, context)


# ******************************
# PSI evaluation on tree
# ******************************
# ******************************
# PSI evaluation on tree
# ******************************

#@250216 cash_out_in

def eval_supply_chain_cash(node):


    # by node
    # cash_out = psiのPで、P*price weekly list AP_LT offset
    # cash_in  = psiのSで、P*price weekly list AR_LT offset


    # Count the number of lots for the node
    node.set_lot_counts()

    # Evaluate the current node's costs
    node.revenue, node.profit = node.EvalPlanSIP_cost()



    # Accumulate the revenue and profit
    total_revenue += node.revenue
    total_profit  += node.profit

    # Recursively evaluate child nodes
    for child in node.children:
        total_revenue, total_profit = eval_supply_chain_cost(
            child, total_revenue, total_profit
        )


    return cash_out, cash_in


# = eval_supply_chain_cash(self.root_node_outbound)





def eval_supply_chain_cost(node, total_revenue=0, total_profit=0):
    """
    Recursively evaluates the cost of the supply chain for a given node.
    
    Parameters:
        node (Node): The root node to start the evaluation.
        total_revenue (float): Accumulated total revenue (default 0).
        total_profit (float): Accumulated total profit (default 0).

    Returns:
        Tuple[float, float]: Accumulated total revenue and total profit.
    """
    # Count the number of lots for the node
    node.set_lot_counts()

    # Evaluate the current node's costs
    node.revenue, node.profit = node.EvalPlanSIP_cost()



    # Accumulate the revenue and profit
    total_revenue += node.revenue
    total_profit  += node.profit

    # Recursively evaluate child nodes
    for child in node.children:
        total_revenue, total_profit = eval_supply_chain_cost(
            child, total_revenue, total_profit
        )

    return total_revenue, total_profit









# *****************
# network graph "node" "edge" process
# *****************




def make_edge_weight_capacity(node, child):
    # Calculate stock cost and customs tariff
    child.EvalPlanSIP_cost()

    #@ STOP
    #stock_cost = sum(child.WH_cost[1:])

    customs_tariff = child.customs_tariff_rate * child.cs_direct_materials_costs

    # Determine weight (logistics cost + tax + storage cost)
    cost_portion = 0.5
    weight4nx = max(0, child.cs_cost_total + (customs_tariff * cost_portion))

    # Calculate capacity (3 times the average weekly demand)
    demand_lots = sum(len(node.psi4demand[w][0]) for w in range(53 * node.plan_range))
    ave_demand_lots = demand_lots / (53 * node.plan_range)
    capacity4nx = 3 * ave_demand_lots

    # Add tariff to leaf nodes
    def add_tariff_on_leaf(node, customs_tariff):
        if not node.children:
            node.tariff_on_price += customs_tariff * cost_portion
        else:
            for child in node.children:
                add_tariff_on_leaf(child, customs_tariff)

    add_tariff_on_leaf(node, customs_tariff)

    # Logging for debugging (optional)
    print(f"child.name: {child.name}")
    print(f"weight4nx: {weight4nx}, capacity4nx: {capacity4nx}")

    return weight4nx, capacity4nx




def make_edge_weight_capacity_OLD(node, child):
    # Weight (重み)
    #    - `weight`は、edgeで定義された2つのノード間の移動コストを表す。
    #       物流費、関税、保管コストなどの合計金額に対応する。
    #    - 例えば、物流費用が高い場合、対応するエッジの`weight`は高くなる。
    #     最短経路アルゴリズム(ダイクストラ法)を適用すると適切な経路を選択する。
    #
    #    self.demandにセット?
    #

    # *********************
    # add_edge_parameter_set_weight_capacity()
    # add_edge()の前処理
    # *********************
    # capacity
    # - `capacity`は、エッジで定義された2つのノード間における期間当たりの移動量
    #   の制約を表します。
    # - サプライチェーンの場合、以下のアプリケーション制約条件を考慮して
    #   ネック条件となる最小値を設定する。
    #     - 期間内のノード間物流の容量の上限値
    #     - 通関の期間内処理量の上限値
    #     - 保管倉庫の上限値
    #     - 出庫・出荷作業の期間内処理量の上限値


    # *****************************************************
    # 在庫保管コストの算定のためにevalを流す
    # 子ノード child.
    # *****************************************************
    stock_cost = 0

    #@ 要確認
    #@241231 ココは新しいcost_tableで評価する
    child.EvalPlanSIP_cost()

    stock_cost = child.eval_WH_cost = sum(child.WH_cost[1:])

    customs_tariff = 0

    #@241231 関税率 X 仕入れ単価とする
    customs_tariff = child.customs_tariff_rate * child.cs_direct_materials_costs

    print("child.name", child.name)
    print("child.customs_tariff_rate", child.customs_tariff_rate)
    print("child.cs_direct_materials_costs", child.cs_direct_materials_costs)
    print("customs_tariff", customs_tariff)

    print("self.cs_price_sales_shipped", node.cs_price_sales_shipped)
    print("self.cs_cost_total", node.cs_cost_total)
    print("self.cs_profit", node.cs_profit)


    #関税コストの吸収方法 1
    # 1. 利益を維持し、コストと価格に上乗せする。
    # 2. 価格を維持し、コストに上乗せし、利益を削る。

    #    self.cs_price_sales_shipped # revenue
    #    self.cs_cost_total          # cost
    #    self.cs_profit              # profit


    #@ OLD STOP
    # 関税率 X 単価
    #customs_tariff = child.customs_tariff_rate * child.REVENUE_RATIO



    weight4nx = 0


    # 物流コスト
    # + TAX customs_tariff
    # + 在庫保管コスト
    # weight4nx = child.Distriburion_Cost + customs_tariff + stock_cost


    #@241231 仮定:関税の増分50%を利益削減する
    cost_portion = 0.5  # price_portion = 0.5 is following

    #@ RUN 
    weight4nx = child.cs_cost_total + (customs_tariff * cost_portion)



    #@ STOP
    #weight4nx = child.cs_profit_accume - (customs_tariff * cost_portion)
    #weight4nx =100*2 - child.cs_profit_accume + (customs_tariff *cost_portion)

    #print("child.cs_profit_accume", child.cs_profit_accume)

    print("child.cs_cost_total", child.cs_cost_total)

    print("customs_tariff", customs_tariff)
    print("cost_portion", cost_portion)
    print("weight4nx", weight4nx)



    if weight4nx < 0:
        weight4nx = 0


    # 出荷コストはPO_costに含まれている
    ## 出荷コスト
    # + xxxx

    #print("child.Distriburion_Cost", child.Distriburion_Cost)
    #print("+ TAX customs_tariff", customs_tariff)
    #print("+ stock_cost", stock_cost)
    #print("weight4nx", weight4nx)

    # ******************************
    # capacity4nx = 3 * average demand lots # ave weekly demand の3倍のcapa
    # ******************************
    capacity4nx = 0

    # ******************************
    # average demand lots
    # ******************************
    demand_lots = 0
    ave_demand_lots = 0

    for w in range(53 * node.plan_range):
        demand_lots += len(node.psi4demand[w][0])

    ave_demand_lots = demand_lots / (53 * node.plan_range)

    #@241231 仮定:関税の増分50%を価格増加による需要曲線上の価格弾力性=1とする
    # on the demand curve,
    # assume a price elasticity of demand of 1 due to price increase.

    #    self.cs_price_sales_shipped # revenue

    # demand_on_curve 需要曲線上の需要
    # customs_tariff*0.5 関税の50%
    # self.cs_price_sales_shipped 売上

    # 価格弾力性による需要変化
    # customs_tariff*0.5 / self.cs_price_sales_shipped 価格増加率
    # self.price_elasticity
    # 0.0: demand "stay" like a medecine
    # 1.0: demand_decrease = price_increse * 1
    # 2.0: demand_decrease = price_increse * 2

    #@241231 MEMO demand_curve
    # 本来、demandは価格上昇時に末端市場leaf_nodeで絞られるが、
    # ここでは、通関時の中間nodeのcapacityでdemandを絞ることで同様の効果とする

    # 末端価格ではないので、関税による価格増減率が異なる?
    # customs_tariff:関税増分のcostを退避しておく、self.customs_tariff
    # leaf_nodeの末端価格のdemand_on_curve = 価格増加率 * node.price_elasticity


    # (customs_tariff * 0.5) をlead_nodeのnode.tariff_on_priceにadd

    def add_tariff_on_leaf(node, customs_tariff):

        price_portion = 0.5 # cost_portion = 0.5 is previously defined

        if node.children == []:  # leaf_node
            node.tariff_on_price += customs_tariff * price_portion # 0.5
        else:
            for child in node.children:
                add_tariff_on_leaf(child, customs_tariff)

    add_tariff_on_leaf(node, customs_tariff)

    #@ STOP
    #demand_on_curve = 3 * ave_demand_lots * (1-(customs_tariff*0.5 / node.cs_price_sales_shipped) * node.price_elasticity )
    #
    #capacity4nx = demand_on_curve       # 


    #@ STOP RUN
    capacity4nx = 3 * ave_demand_lots  # N * ave weekly demand

    print("weight4nx", weight4nx)
    print("capacity4nx", capacity4nx)

    return weight4nx, capacity4nx  # ココはfloatのまま戻す








def G_add_edge_from_tree(node, G):

    if node.children == []:  # leaf_nodeを判定

        # ******************************
        # capacity4nx = average demand lots # ave weekly demand をそのままset
        # ******************************
        capacity4nx = 0
        demand_lots = 0
        ave_demand_lots = 0

        for w in range(53 * node.plan_range):
            demand_lots += len(node.psi4demand[w][0])

        ave_demand_lots = demand_lots / (53 * node.plan_range)

        capacity4nx = ave_demand_lots  # N * ave weekly demand


        # ******************************
        # edge connecting leaf_node and "sales_office" 接続
        # ******************************

        #@ RUN X1
        capacity4nx_int = round(capacity4nx) + 1

        #@ STOP
        # float2int X100
        #capacity4nx_int = float2int(capacity4nx)

        G.add_edge(node.name, "sales_office",
                 weight=0,
                 #capacity=capacity4nx_int
                 capacity=2000
        )

        print(
            "G.add_edge(node.name, office",
            node.name,
            "sales_office",
            "weight = 0, capacity =",
            capacity4nx,
        )

        # pass

    else:

        for child in node.children:

            # *****************************
            # make_edge_weight_capacity
            # *****************************
            weight4nx, capacity4nx = make_edge_weight_capacity(node, child)

            # float2int
            weight4nx_int = float2int(weight4nx)

            #@ RUN X1
            capacity4nx_int = round(capacity4nx) + 1

            #@ STOP
            # float2int X100
            #capacity4nx_int = float2int(capacity4nx)

            child.nx_weight = weight4nx_int
            child.nx_capacity = capacity4nx_int

            # ******************************
            # edge connecting self.node & child.node
            # ******************************

            G.add_edge(
                node.name, child.name, 
                weight=weight4nx_int,

                #capacity=capacity4nx_int
                capacity=2000

            )

            print(
                "G.add_edge(node.name, child.name",
                node.name,
                child.name,
                "weight =",
                weight4nx_int,
                "capacity =",
                capacity4nx_int,
            )

            G_add_edge_from_tree(child, G)





def Gsp_add_edge_sc2nx_inbound(node, Gsp):

    if node.children == []:  # leaf_nodeを判定

        # ******************************
        # capacity4nx = average demand lots # ave weekly demand をそのままset
        # ******************************
        capacity4nx = 0
        demand_lots = 0
        ave_demand_lots = 0

        for w in range(53 * node.plan_range):
            demand_lots += len(node.psi4demand[w][0])

        ave_demand_lots = demand_lots / (53 * node.plan_range)

        capacity4nx = ave_demand_lots  # N * ave weekly demand

        # ******************************
        # edge connecting leaf_node and "sales_office" 接続
        # ******************************

        # float2int
        capacity4nx_int = float2int(capacity4nx)

        Gsp.add_edge( "procurement_office", node.name,
                 weight=0,
                 capacity = 2000 # 240906 TEST # capacity4nx_int * 1 # N倍
                 #capacity=capacity4nx_int * 1 # N倍
        )

        # pass

    else:

        for child in node.children:

            # *****************************
            # make_edge_weight_capacity
            # *****************************
            weight4nx, capacity4nx = make_edge_weight_capacity(node, child)

            # float2int
            weight4nx_int = float2int(weight4nx)
            capacity4nx_int = float2int(capacity4nx)

            #@240906 TEST 
            capacity4nx_int = 2000

            child.nx_weight = weight4nx_int
            child.nx_capacity = capacity4nx_int

            # ******************************
            # edge connecting self.node & child.node
            # ******************************

            Gsp.add_edge(
                child.name, node.name, 
                weight=weight4nx_int,

                capacity=capacity4nx_int
            )

            Gsp_add_edge_sc2nx_inbound(child, Gsp)





def Gdm_add_edge_sc2nx_outbound(node, Gdm):

    if node.children == []:  # leaf_nodeを判定

        # ******************************
        # capacity4nx = average demand lots # ave weekly demand をそのままset
        # ******************************
        capacity4nx = 0
        demand_lots = 0
        ave_demand_lots = 0

        for w in range(53 * node.plan_range):
            demand_lots += len(node.psi4demand[w][0])



        ave_demand_lots = demand_lots / (53 * node.plan_range)

        #@ STOP
        #capacity4nx = ave_demand_lots  # N * ave weekly demand

        tariff_portion = node.tariff_on_price / node.cs_price_sales_shipped

        demand_on_curve = 3 * ave_demand_lots * (1- tariff_portion) * node.price_elasticity 


        print("node.name", node.name)

        print("node.tariff_on_price", node.tariff_on_price)
        print("node.cs_price_sales_shipped", node.cs_price_sales_shipped)
        print("tariff_portion", tariff_portion)

        print("ave_demand_lots", ave_demand_lots)
        print("node.price_elasticity", node.price_elasticity)
        print("demand_on_curve", demand_on_curve)



        #demand_on_curve = 3 * ave_demand_lots * (1-(customs_tariff*0.5 / node.cs_price_sales_shipped) * node.price_elasticity )

        capacity4nx = demand_on_curve       # 


        print("capacity4nx", capacity4nx)



        # ******************************
        # edge connecting leaf_node and "sales_office" 接続
        # ******************************

        # float2int
        capacity4nx_int = float2int(capacity4nx)

        # set PROFIT 2 WEIGHT

        Gdm.add_edge(node.name, "sales_office",
                 weight=0,
                 capacity=capacity4nx_int * 1 # N倍
        )

        print(
            "Gdm.add_edge(node.name, office",
            node.name,
            "sales_office",
            "weight = 0, capacity =",
            capacity4nx,
        )

        # pass

    else:

        for child in node.children:

            # *****************************
            # make_edge_weight_capacity
            # *****************************
            weight4nx, capacity4nx = make_edge_weight_capacity(node, child)

            # float2int
            weight4nx_int = float2int(weight4nx)
            capacity4nx_int = float2int(capacity4nx)

            child.nx_weight = weight4nx_int
            child.nx_capacity = capacity4nx_int

            # ******************************
            # edge connecting self.node & child.node
            # ******************************

            Gdm.add_edge(
                node.name, child.name, 
                weight=weight4nx_int,

                capacity=capacity4nx_int
            )

            print(
                "Gdm.add_edge(node.name, child.name",
                node.name, child.name,
                "weight =", weight4nx_int,
                "capacity =", capacity4nx_int
            )

            Gdm_add_edge_sc2nx_outbound(child, Gdm)






def make_edge_weight(node, child):


#NetworkXでは、エッジの重み（weight）が大きい場合、そのエッジの利用優先度は、アルゴリズムや目的によって異なる

    # Weight (重み)
    #    - `weight`はedgeで定義された2ノード間で発生するprofit(rev-cost)で表す
    #       cost=物流費、関税、保管コストなどの合計金額に対応する。
    #    - 例えば、物流費用が高い場合、対応するエッジの`weight`は低くなる。
    #     最短経路アルゴリズム(ダイクストラ法)を適用すると適切な経路を選択する。

#最短経路アルゴリズム（例：Dijkstra’s algorithm）では、エッジの重みが大きいほど、そのエッジを通る経路のコストが高くなるため、優先度は下がる

#最大フロー問題などの他のアルゴリズムでは、エッジの重みが大きいほど、そのエッジを通るフローが多くなるため、優先度が上がることがある
#具体的な状況や使用するアルゴリズムによって異なるため、
#目的に応じて適切なアルゴリズムを選択することが重要

# 最大フロー問題（Maximum Flow Problem）
# フォード・ファルカーソン法 (Ford-Fulkerson Algorithm)
#フォード・ファルカーソン法は、ネットワーク内のソース（始点）からシンク（終点）までの最大フローを見つけるアルゴリズム
#このアルゴリズムでは、エッジの重み（容量）が大きいほど、そのエッジを通るフローが多くなるため、優先度が上がります。


#@240831 
#    # *****************************************************
#    # 在庫保管コストの算定のためにevalを流す
#    # 子ノード child.
#    # *****************************************************
#
#    stock_cost = 0
#
#    child.EvalPlanSIP()
#
#    stock_cost = child.eval_WH_cost = sum(child.WH_cost[1:])
#
#    customs_tariff = 0
#    customs_tariff = child.customs_tariff_rate * child.REVENUE_RATIO  # 関税率 X 単価
#
#    # 物流コスト
#    # + TAX customs_tariff
#    # + 在庫保管コスト
#    # weight4nx = child.Distriburion_Cost + customs_tariff + stock_cost


    # priority is "profit"

    weight4nx = 0

    weight4nx = child.cs_profit_accume

    return weight4nx






#@240830 コこを修正
# 1.capacityの計算は、supply sideで製品ロット単位の統一したroot_capa * N倍
# 2.自node=>親nodeの関係定義 G.add_edge(self.node, parent.node)

def G_add_edge_from_inbound_tree(node, supplyers_capacity, G):

    if node.children == []:  # leaf_nodeを判定

        # ******************************
        # capacity4nx = average demand lots # ave weekly demand *N倍をset
        # ******************************
        capacity4nx = 0

        # 
        # ******************************
        #demand_lots = 0
        #ave_demand_lots = 0
        #
        #for w in range(53 * node.plan_range):
        #    demand_lots += len(node.psi4demand[w][0])
        #
        #ave_demand_lots = demand_lots / (53 * node.plan_range)
        #
        #capacity4nx = ave_demand_lots * 5  # N * ave weekly demand
        #
        # ******************************

        # supplyers_capacityは、root_node=mother plantのcapacity
        # 末端suppliersは、平均の5倍のcapa
        capacity4nx = supplyers_capacity * 5  # N * ave weekly demand


        # float2int
        capacity4nx_int = float2int(capacity4nx)

        # ******************************
        # edge connecting leaf_node and "procurement_office" 接続
        # ******************************

        G.add_edge("procurement_office", node.name, weight=0, capacity=2000)

        #G.add_edge("procurement_office", node.name, weight=0, capacity=capacity4nx_int)

        print(
            "G.add_edge(node.name, office",
            node.name,
            "sales_office",
            "weight = 0, capacity =",
            capacity4nx,
        )

        # pass

    else:

        for child in node.children:


            # supplyers_capacityは、root_node=mother plantのcapacity
            # 中間suppliersは、平均の3倍のcapa
            capacity4nx = supplyers_capacity * 3  # N * ave weekly demand


            # *****************************
            # set_edge_weight
            # *****************************
            weight4nx = make_edge_weight(node, child)

            ## *****************************
            ## make_edge_weight_capacity
            ## *****************************
            #weight4nx, capacity4nx = make_edge_weight_capacity(node, child)



            # float2int
            weight4nx_int = float2int(weight4nx)
            capacity4nx_int = float2int(capacity4nx)

            child.nx_weight = weight4nx_int
            child.nx_capacity = capacity4nx_int

            # ******************************
            # edge connecting from child.node to self.node as INBOUND
            # ******************************
            #G.add_edge(
            #    child.name, node.name, 
            #    weight=weight4nx_int, capacity=capacity4nx_int
            #)

            G.add_edge(
                child.name, node.name, 
                weight=weight4nx_int, capacity=2000
            )

            #print(
            #    "G.add_edge(child.name, node.name ",
            #    child.name,
            #    node.name,
            #    "weight =",
            #    weight4nx_int,
            #    "capacity =", 
            #    capacity4nx_int,
            #)

            G_add_edge_from_inbound_tree(child, supplyers_capacity, G)






    # *********************
    # OUT treeを探索してG.add_nodeを処理する
    # node_nameをGにセット (X,Y)はfreeな状態、(X,Y)のsettingは後処理
    # *********************
def G_add_nodes_from_tree(node, G):


    G.add_node(node.name, demand=0)
    #G.add_node(node.name, demand=node.nx_demand) #demandは強い制約でNOT set!!

    print("G.add_node", node.name, "demand =", node.nx_demand)

    if node.children == []:  # leaf_nodeの場合、total_demandに加算

        pass

    else:

        for child in node.children:

            G_add_nodes_from_tree(child, G)



    # *********************
    # IN treeを探索してG.add_nodeを処理する。ただし、root_node_inboundをskip
    # node_nameをGにセット (X,Y)はfreeな状態、(X,Y)のsettingは後処理
    # *********************
def G_add_nodes_from_tree_skip_root(node, root_node_name_in, G):

    #@240901STOP
    #if node.name == root_node_name_in:
    #
    #    pass
    #
    #else:
    #
    #    G.add_node(node.name, demand=0)
    #    print("G.add_node", node.name, "demand = 0")

    G.add_node(node.name, demand=0)
    print("G.add_node", node.name, "demand = 0")

    if node.children == []:  # leaf_nodeの場合

        pass

    else:

        for child in node.children:

            G_add_nodes_from_tree_skip_root(child, root_node_name_in, G)
        





# *****************
# demand, weight and scaling FLOAT to INT
# *****************
def float2int(value):

    scale_factor = 100
    scaled_demand = value * scale_factor

    # 四捨五入
    rounded_demand = round(scaled_demand)
    # print(f"四捨五入: {rounded_demand}")

    ## 切り捨て
    # floored_demand = math.floor(scaled_demand)
    # print(f"切り捨て: {floored_demand}")

    ## 切り上げ
    # ceiled_demand = math.ceil(scaled_demand)
    # print(f"切り上げ: {ceiled_demand}")

    return rounded_demand



# *********************
# 末端市場、最終消費の販売チャネルのdemand = leaf_node_demand
# treeのleaf nodesを探索して"weekly average base"のtotal_demandを集計
# *********************
def set_leaf_demand(node, total_demand):

    if node.children == []:  # leaf_nodeの場合、total_demandに加算

        # ******************************
        # average demand lots
        # ******************************
        demand_lots = 0
        ave_demand_lots = 0
        ave_demand_lots_int = 0

        for w in range(53 * node.plan_range):
            demand_lots += len(node.psi4demand[w][0])

        ave_demand_lots = demand_lots / (53 * node.plan_range)

        # float2int
        ave_demand_lots_int = float2int(ave_demand_lots)


        # **** networkX demand *********
        # set demand on leaf_node    
        # weekly average demand by lot
        # ******************************
        node.nx_demand = ave_demand_lots_int


        total_demand += ave_demand_lots_int

    else:

        for child in node.children:

            # "行き" GOing on the way

            total_demand = set_leaf_demand(child, total_demand)


            # "帰り" RETURNing on the way BACK
            node.nx_demand = child.nx_demand  # set "middle_node" demand


    return total_demand





# ***************************
# make network with NetworkX
# show network with plotly
# ***************************



def calc_put_office_position(pos_office, office_name):
    x_values = [pos_office[key][0] for key in pos_office]
    max_x = max(x_values)
    y_values = [pos_office[key][1] for key in pos_office]
    max_y = max(y_values)
    pos_office[office_name] = (max_x + 1, max_y + 1)
    return pos_office

def generate_positions(node, pos, depth=0, y_offset=0, leaf_y_positions=None):
    if not node.children:
        pos[node.name] = (depth, leaf_y_positions.pop(0))
    else:
        child_y_positions = []
        for child in node.children:
            generate_positions(child, pos, depth + 1, y_offset, leaf_y_positions)
            child_y_positions.append(pos[child.name][1])
        pos[node.name] = (depth, sum(child_y_positions) / len(child_y_positions))  # 子ノードのY軸平均値を親ノードに設定
    return pos

def count_leaf_nodes(node):
    if not node.children:
        return 1
    return sum(count_leaf_nodes(child) for child in node.children)

def get_leaf_y_positions(node, y_positions=None):
    if y_positions is None:
        y_positions = []
    if not node.children:
        y_positions.append(len(y_positions))
    else:
        for child in node.children:
            get_leaf_y_positions(child, y_positions)
    return y_positions

def tune_hammock(pos_E2E, nodes_outbound, nodes_inbound):
    # Compare 'procurement_office' and 'sales_office' Y values and choose the larger one
    procurement_office_y = pos_E2E['procurement_office'][1]
    office_y = pos_E2E['sales_office'][1]

    max_y = max(procurement_office_y, office_y)
    
    pos_E2E['procurement_office'] = (pos_E2E['procurement_office'][0], max_y)
    pos_E2E['sales_office'] = (pos_E2E['sales_office'][0], max_y)

    # Align 'FA_xxxx' and 'PL_xxxx' pairs and their children
    for key, value in pos_E2E.items():
        if key.startswith('MOM'):
            corresponding_key = 'DAD' + key[3:]
            if corresponding_key in pos_E2E:
                fa_y = value[1]
                pl_y = pos_E2E[corresponding_key][1]
                aligned_y = max(fa_y, pl_y)
                pos_E2E[key] = (value[0], aligned_y)
                pos_E2E[corresponding_key] = (pos_E2E[corresponding_key][0], aligned_y)


                offset_y = max( aligned_y - fa_y, aligned_y - pl_y )

                if aligned_y - fa_y == 0: # inboundの高さが同じ outboundを調整
                    
                    pool_node = nodes_outbound[corresponding_key]
                    adjust_child_positions(pool_node, pos_E2E, offset_y)

                else:

                    fassy_node = nodes_inbound[key]
                    adjust_child_positions(fassy_node, pos_E2E, offset_y)



                ## Adjust children nodes
                #adjust_child_positions(pos_E2E, key, aligned_y)
                #adjust_child_positions(pos_E2E, corresponding_key, aligned_y)

    return pos_E2E

#def adjust_child_positions(pos, parent_key, parent_y):
#    for key, value in pos.items():
#        if key != parent_key and pos[key][0] > pos[parent_key][0]:
#            pos[key] = (value[0], value[1] + (parent_y - pos[parent_key][1]))


def adjust_child_positions(node, pos, offset_y):
    if node.children == []:  # leaf_nodeを判定
        pass
    else:
        for child in node.children:
            # yの高さを調整 
            pos[child.name] = (pos[child.name][0], pos[child.name][1]+offset_y)
            adjust_child_positions(child, pos, offset_y)


def make_E2E_positions(root_node_outbound, root_node_inbound):
    out_leaf_count = count_leaf_nodes(root_node_outbound)
    in_leaf_count = count_leaf_nodes(root_node_inbound)

    print("out_leaf_count", out_leaf_count)
    print("in_leaf_count", in_leaf_count)

    out_leaf_y_positions = get_leaf_y_positions(root_node_outbound)
    in_leaf_y_positions = get_leaf_y_positions(root_node_inbound)

    pos_out = generate_positions(root_node_outbound, {}, leaf_y_positions=out_leaf_y_positions)
    pos_out = calc_put_office_position(pos_out, "sales_office")

    pos_in = generate_positions(root_node_inbound, {}, leaf_y_positions=in_leaf_y_positions)
    pos_in = calc_put_office_position(pos_in, "procurement_office")

    max_x = max(x for x, y in pos_in.values())
    pos_in_reverse = {node: (max_x - x, y) for node, (x, y) in pos_in.items()}
    pos_out_shifting = {node: (x + max_x, y) for node, (x, y) in pos_out.items()}

    merged_dict = pos_in_reverse.copy()
    for key, value in pos_out_shifting.items():
        if key in merged_dict:
            if key == root_node_outbound.name:
                merged_dict[key] = value if value[1] > merged_dict[key][1] else merged_dict[key]
            else:
                merged_dict[key] = value
        else:
            merged_dict[key] = value

    pos_E2E = merged_dict

    return pos_E2E











if __name__ == "__main__":

    # Example usage
    example_tree = {
        "root": ["child1", "child2"],
        "child1": ["child1_1", "child1_2"],
        "child2": ["child2_1"]
    }

    root_node = build_tree_from_dict(example_tree)
    root_node.print_tree()


