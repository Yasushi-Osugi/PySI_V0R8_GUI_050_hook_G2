






#250114gui_app.py

# gui/app.py

# ********************************
# library import
# ********************************
import os
import shutil
import threading

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import font as tkfont, Tk, Menu, ttk
from tkinter.constants import BOTH, Y, X  # Import BOTH, Y, and X constants

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


import networkx as nx


import datetime as dt
from datetime import datetime as dt_datetime, timedelta

import math

import copy
import pickle

# ********************************
# library import
# ********************************

#import mpld3
#from mpld3 import plugins


from collections import defaultdict


import numpy as np

from dateutil.relativedelta import relativedelta

import calendar


# ********************************
# Allocation logic
# ********************************
import csv
from datetime import date, timedelta
from math import floor



# ********************************
# PySI library import
# ********************************
from pysi.utils.config import Config

from pysi.utils.file_io import *
#from utils.file_io import load_cost_table
#from utils.file_io import load_monthly_demand


from pysi.utils.calendar445 import Calendar445


from pysi.plan.demand_generate import convert_monthly_to_weekly

from pysi.plan.operations import *
# "plan.demand_processing" is merged in "plan.operations"

#from plan.demand_processing import *
#from pysi.plan.demand_processing import set_df_Slots2psi4demand


from pysi.network.tree import *
#from network.tree import create_tree_set_attribute
#from network.tree import set_node_costs

#from network.tree import calc_all_psi2i4demand, set_lot_counts

#from PSI_plan.planning_operation import calcS2P, set_S2psi, get_set_childrenP2S2psi, calc_all_psi2i4demand, calcPS2I4demand





# ********************************
# Definition start
# ********************************






def find_all_paths(node, path, paths):
    path.append(node.name)

    if not node.children:

        #print("leaf path", node.name, path)
        paths.append(path.copy())

    else:

        for child in node.children:

            # print("child path",child.name, path)

            find_all_paths(child, path, paths)

            for grandchild in child.children:
                #print("grandchild path", grandchild.name, path)
                find_all_paths(grandchild, path, paths)

                for g_grandchild in grandchild.children:
                    #print("g_grandchild path", g_grandchild.name, path)
                    find_all_paths(g_grandchild, path, paths)

                    for g1_grandchild in g_grandchild.children:
                        #print("g1_grandchild path", g1_grandchild.name, path)
                        find_all_paths(g1_grandchild, path, paths)

                        for g2_grandchild in g1_grandchild.children:
                            #print("g2_grandchild path", g2_grandchild.name, path)
                            find_all_paths(g2_grandchild, path, paths)

    path.pop()


def find_paths(root):

    paths = []

    find_all_paths(root, [], paths)

    return paths





# *********************************
# check_plan_range
# *********************************
def check_plan_range(df):  # df is dataframe

    #
    # getting start_year and end_year
    #
    start_year = node_data_min = df["year"].min()
    end_year = node_data_max = df["year"].max()

    # *********************************
    # plan initial setting
    # *********************************

    plan_year_st = int(start_year)  # 2024  # plan開始年

    # 3ヵ年または5ヵ年計画分のS計画を想定
    plan_range = int(end_year) - int(start_year) + 1 + 1  # +1はハミ出す期間

    plan_year_end = plan_year_st + plan_range

    return plan_range, plan_year_st


# 2. lot_id_list列を追加
def generate_lot_ids(row):

    # node_yyyy_ww = f"{row['node_name']}_{row['iso_year']}_{row['iso_week']}"
    node_yyyy_ww = f"{row['node_name']}{row['iso_year']}{row['iso_week']}"

    lots_count = row["S_lot"]

    # stack_list = [f"{node_yyyy_ww}_{i}" for i in range(lots_count)]

    #@240930 修正MEMO
    # ココの{i}をzfillで二桁にする
    #stack_list = [f"{node_yyyy_ww}{i:02}" for i in range(lots_count)]

    digit_count = 2
    stack_list = [f"{node_yyyy_ww}{str(i).zfill(digit_count)}" for i in range(lots_count)]

    return stack_list




# ******************************
# trans month 2 week 2 lot_id_list
# ******************************
def trans_month2week2lot_id_list(file_name, lot_size):

    df = pd.read_csv(file_name)

    # *********************************
    # check_plan_range
    # *********************************
    plan_range, plan_year_st = check_plan_range(df)  # df is dataframe

    df = df.melt(
        id_vars=["product_name", "node_name", "year"],
        var_name="month",
        value_name="value",
    )

    df["month"] = df["month"].str[1:].astype(int)

    df_daily = pd.DataFrame()

    for _, row in df.iterrows():

        daily_values = np.full(
            pd.Timestamp(row["year"], row["month"], 1).days_in_month, row["value"]
        )

        dates = pd.date_range(
            start=f"{row['year']}-{row['month']}-01", periods=len(daily_values)
        )

        df_temp = pd.DataFrame(
            {
                "product_name": row["product_name"],
                "node_name": row["node_name"],
                "date": dates,
                "value": daily_values,
            }
        )

        df_daily = pd.concat([df_daily, df_temp])


    #@24240930 STOP
    #df_daily["iso_year"] = df_daily["date"].dt.isocalendar().year
    #df_daily["iso_week"] = df_daily["date"].dt.isocalendar().week
    #
    #df_weekly = (
    #    df_daily.groupby(["product_name", "node_name", "iso_year", "iso_week"])["value"]
    #    .sum()
    #    .reset_index()
    #)


    df_daily["iso_year"] = df_daily["date"].dt.isocalendar().year

    # ISO週を２ケタ表示
    df_daily["iso_week"] = df_daily["date"].dt.isocalendar().week.astype(str).str.zfill(2)

    df_weekly = (
        df_daily.groupby(["product_name", "node_name", "iso_year", "iso_week"])["value"]
        .sum()
        .reset_index()
    )

    ## 1. S_lot列を追加
    # lot_size = 100  # ここに適切なlot_sizeを設定します
    df_weekly["S_lot"] = df_weekly["value"].apply(lambda x: math.ceil(x / lot_size))

    ## 2. lot_id_list列を追加
    # def generate_lot_ids(row):
    df_weekly["lot_id_list"] = df_weekly.apply(generate_lot_ids, axis=1)

    return df_weekly, plan_range, plan_year_st




def make_capa_year_month(input_file):

    #    # mother plant capacity parameter
    #    demand_supply_ratio = 1.2  # demand_supply_ratio = ttl_supply / ttl_demand

    # initial setting of total demand and supply
    # total_demandは、各行のm1からm12までの列の合計値

    df_capa = pd.read_csv(input_file)

    df_capa["total_demand"] = df_capa.iloc[:, 3:].sum(axis=1)

    # yearでグループ化して、月次需要数の総和を計算
    df_capa_year = df_capa.groupby(["year"], as_index=False).sum()

    return df_capa_year




#def trans_month2week2lot_id_list(file_name, lot_size)
def process_monthly_demand(file_name, lot_size):
    """
    Process monthly demand data and convert to weekly data.

    Parameters:
        file_name (str): Path to the monthly demand file.
        lot_size (int): Lot size for allocation.

    Returns:
        pd.DataFrame: Weekly demand data with ISO weeks and lot IDs.
    """
    monthly_data = load_monthly_demand(file_name)
    if monthly_data.empty:
        print("Error: Failed to load monthly demand data.")
        return None

    return convert_monthly_to_weekly(monthly_data, lot_size)




def read_set_cost(file_path, nodes_outbound):
    """
    Load cost table from file and set node costs.

    Parameters:
        file_path (str): Path to the cost table file.
        nodes_outbound (dict): Dictionary of outbound nodes.

    Returns:
        None
    """
    cost_table = load_cost_table(file_path)

    if cost_table is not None:
        set_node_costs(cost_table, nodes_outbound)




# ****************************
# 辞書をtree nodeのdemand & supplyに接続する
# ****************************
def set_dict2tree_psi(node, attr_name, node_psi_dict):

    setattr(node, attr_name, node_psi_dict.get(node.name))

    # node.psi4supply = node_psi_dict.get(node.name)

    for child in node.children:

        set_dict2tree_psi(child, attr_name, node_psi_dict)


# nodeを手繰りながらnode_psi_dict辞書を初期化する
def make_psi_space_dict(node, node_psi_dict, plan_range):

    psi_list = [[[] for j in range(4)] for w in range(53 * plan_range)]

    node_psi_dict[node.name] = psi_list  # 新しいdictにpsiをセット

    for child in node.children:

        make_psi_space_dict(child, node_psi_dict, plan_range)

    return node_psi_dict




# *******************
# 生産平準化の前処理　ロット・カウント
# *******************
def count_lots_yyyy(psi_list, yyyy_str):

    matrix = psi_list

    # 共通の文字列をカウントするための変数を初期化
    count_common_string = 0

    # Step 1: マトリクス内の各要素の文字列をループで調べる
    for row in matrix:

        for element in row:

            # Step 2: 各要素内の文字列が "2023" を含むかどうかを判定
            if yyyy_str in element:

                # Step 3: 含む場合はカウンターを増やす
                count_common_string += 1

    return count_common_string


def is_52_or_53_week_year(year):
    # 指定された年の12月31日を取得
    last_day_of_year = dt.date(year, 12, 31)

    # 12月31日のISO週番号を取得 (isocalendar()メソッドはタプルで[ISO年, ISO週番号, ISO曜日]を返す)
    _, iso_week, _ = last_day_of_year.isocalendar()

    # ISO週番号が1の場合は前年の最後の週なので、52週と判定
    if iso_week == 1:
        return 52
    else:
        return iso_week


def find_depth(node):
    if not node.parent:
        return 0
    else:
        return find_depth(node.parent) + 1


def find_all_leaves(node, leaves, depth=0):
    if not node.children:
        leaves.append((node, depth))  # (leafノード, 深さ) のタプルを追加
    else:
        for child in node.children:
            find_all_leaves(child, leaves, depth + 1)


def make_nodes_decouple_all(node):

    #
    #    root_node = build_tree()
    #    set_parent(root_node)

    #    leaves = []
    #    find_all_leaves(root_node, leaves)
    #    pickup_list = leaves[::-1]  # 階層の深い順に並べる

    leaves = []
    leaves_name = []

    nodes_decouple = []

    find_all_leaves(node, leaves)
    # find_all_leaves(root_node, leaves)
    pickup_list = sorted(leaves, key=lambda x: x[1], reverse=True)
    pickup_list = [leaf[0] for leaf in pickup_list]  # 深さ情報を取り除く

    # こうすることで、leaf nodeを階層の深い順に並べ替えた pickup_list が得られます。
    # 先に深さ情報を含めて並べ替え、最後に深さ情報を取り除くという流れになります。

    # 初期処理として、pickup_listをnodes_decoupleにcopy
    # pickup_listは使いまわしで、pop / insert or append / removeを繰り返す
    for nd in pickup_list:
        nodes_decouple.append(nd.name)

    nodes_decouple_all = []

    while len(pickup_list) > 0:

        # listのcopyを要素として追加
        nodes_decouple_all.append(nodes_decouple.copy())

        current_node = pickup_list.pop(0)
        del nodes_decouple[0]  # 並走するnode.nameの処理

        parent_node = current_node.parent

        if parent_node is None:
            break

        # 親ノードをpick up対象としてpickup_listに追加
        if current_node.parent:

            #    pickup_list.append(current_node.parent)
            #    nodes_decouple.append(current_node.parent.name)

            # if parent_node not in pickup_list:  # 重複追加を防ぐ

            # 親ノードの深さを見て、ソート順にpickup_listに追加
            depth = find_depth(parent_node)
            inserted = False

            for idx, node in enumerate(pickup_list):

                if find_depth(node) <= depth:

                    pickup_list.insert(idx, parent_node)
                    nodes_decouple.insert(idx, parent_node.name)

                    inserted = True
                    break

            if not inserted:
                pickup_list.append(parent_node)
                nodes_decouple.append(parent_node.name)

            # 親ノードから見た子ノードをpickup_listから削除
            for child in parent_node.children:

                if child in pickup_list:

                    pickup_list.remove(child)
                    nodes_decouple.remove(child.name)

        else:

            print("error: node dupplicated", parent_node.name)

    return nodes_decouple_all






    # +++++++++++++++++++++++++++++++++++++++++++++++
    # Mother Plant demand leveling 
    # root_node_outbound / supply / [w][0] setting S_allocated&pre_prod&leveled
    # +++++++++++++++++++++++++++++++++++++++++++++++
def demand_leveling_on_ship(root_node_outbound, pre_prod_week, year_st, year_end):

    # input: root_node_outbound.psi4demand
    #        pre_prod_week =26 
    #
    # output:root_node_outbound.psi4supply

    plan_range = root_node_outbound.plan_range


    #@241114
    # 需給バランスの問題は、ひとつ上のネットワーク全体のoptimizeで解く

    # ロット単位で供給を変化させて、weight=ロット(CPU_profit)利益でsimulate
    # 設備投資の回収期間を見る

    # 供給>=需要ならオペレーション問題
    # 供給<需要なら供給配分とオペレーション問題

    # optimiseで、ルートと量を決定
    # PSIで、operation revenue cost profitを算定 business 評価

    # 業界No1/2/3の供給戦略をsimulateして、business評価する


    # node_psi_dict_Ot4Dmでは、末端市場のleafnodeのみセット
    #
    # root_nodeのS psi_list[w][0]に、levelingされた確定出荷S_confirm_listをセッ    ト

    # 年間の総需要(総lots)をN週先行で生産する。
    # 例えば、３ヶ月先行は13週先行生産として、年間総需要を週平均にする。

    # S出荷で平準化して、confirmedS-I-P
    # conf_Sからconf_Pを生成して、conf_P-S-I  PUSH and PULL

    S_list = []
    S_allocated = []

    year_lots_list = []
    year_week_list = []

    leveling_S_in = []

    leveling_S_in = root_node_outbound.psi4demand

    # psi_listからS_listを生成する
    for psi in leveling_S_in:

        S_list.append(psi[0])

    # 開始年を取得する
    plan_year_st = year_st  # 開始年のセット in main()要修正

    #for yyyy in range(plan_year_st, plan_year_st + plan_range + 1):
    for yyyy in range(int(plan_year_st), int(plan_year_st + plan_range + 1)):

        year_lots = count_lots_yyyy(S_list, str(yyyy))

        year_lots_list.append(year_lots)

    #        # 結果を出力
    #       #print(yyyy, " year carrying lots:", year_lots)
    #
    #    # 結果を出力
    #   #print(" year_lots_list:", year_lots_list)

    # an image of sample data
    #
    # 2023  year carrying lots: 0
    # 2024  year carrying lots: 2919
    # 2025  year carrying lots: 2914
    # 2026  year carrying lots: 2986
    # 2027  year carrying lots: 2942
    # 2028  year carrying lots: 2913
    # 2029  year carrying lots: 0
    #
    # year_lots_list: [0, 2919, 2914, 2986, 2942, 2913, 0]

    year_list = []

    #for yyyy in range(plan_year_st, plan_year_st + plan_range + 1):
    for yyyy in range(int(plan_year_st), int(plan_year_st + plan_range + 1)):

        year_list.append(yyyy)

        # テスト用の年を指定
        year_to_check = yyyy

        # 指定された年のISO週数を取得
        week_count = is_52_or_53_week_year(year_to_check)

        year_week_list.append(week_count)

    #        # 結果を出力
    #       #print(year_to_check, " year has week_count:", week_count)
    #
    #    # 結果を出力
    #   #print(" year_week_list:", year_week_list)

    # print("year_list", year_list)

    # an image of sample data
    #
    # 2023  year has week_count: 52
    # 2024  year has week_count: 52
    # 2025  year has week_count: 52
    # 2026  year has week_count: 53
    # 2027  year has week_count: 52
    # 2028  year has week_count: 52
    # 2029  year has week_count: 52
    # year_week_list: [52, 52, 52, 53, 52, 52, 52]


    # *****************************
    # 生産平準化のための年間の週平均生産量(ロット数単位)
    # *****************************

    # *****************************
    # make_year_average_lots
    # *****************************
    # year_list     = [2023,2024,2025,2026,2027,2028,2029]

    # year_lots_list = [0, 2919, 2914, 2986, 2942, 2913, 0]
    # year_week_list = [52, 52, 52, 53, 52, 52, 52]

    year_average_lots_list = []

    for lots, weeks in zip(year_lots_list, year_week_list):

        average_lots_per_week = math.ceil(lots / weeks)

        year_average_lots_list.append(average_lots_per_week)


    # print("year_average_lots_list", year_average_lots_list)
    #
    # an image of sample data
    #
    # year_average_lots_list [0, 57, 57, 57, 57, 57, 0]

    # 年間の総需要(総lots)をN週先行で生産する。
    # 例えば、３ヶ月先行は13週先行生産として、年間総需要を週平均にする。

    #
    # 入力データの前提
    #
    # leveling_S_in[w][0] == S_listは、outboundのdemand_planで、
    # マザープラントの出荷ポジションのSで、
    # 5年分 週次 最終市場におけるlot_idリストが
    # LT offsetされた状態で入っている
    #
    # year_list     = [2023,2024,2025,2026,2027,2028,2029]

    # year_lots_list = [0, 2919, 2914, 2986, 2942, 2913, 0]
    # year_week_list = [52, 52, 52, 53, 52, 52, 52]
    # year_average_lots_list [0, 57, 57, 57, 57, 57, 0]

    # ********************************
    # 先行生産の週数
    # ********************************
    # precedence_production_week =13

    pre_prod_week =26 # 26週=6か月の先行生産をセット
    # pre_prod_week =13 # 13週=3か月の先行生産をセット
    # pre_prod_week = 6  # 6週=1.5か月の先行生産をセット

    # ********************************
    # 先行生産の開始週を求める
    # ********************************
    # 市場投入の前年において i= 0  year_list[i]           # 2023
    # 市場投入の前年のISO週の数 year_week_list[i]         # 52

    # 先行生産の開始週は、市場投入の前年のISO週の数 - 先行生産週

    pre_prod_start_week = 0

    i = 0

    pre_prod_start_week = year_week_list[i] - pre_prod_week

    # スタート週の前週まで、[]リストで埋めておく
    for i in range(pre_prod_start_week):
        S_allocated.append([])

    # ********************************
    # 最終市場からのLT offsetされた出荷要求lot_idリストを
    # Allocate demand to mother plant weekly slots
    # ********************************

    # S_listの週別lot_idリストを一直線のlot_idリストに変換する
    # mother plant weekly slots

    # 空リストを無視して、一直線のlot_idリストに変換

    # 空リストを除外して一つのリストに結合する処理
    S_one_list = [item for sublist in S_list if sublist for item in sublist]

    ## 結果表示
    ##print(S_one_list)

    # to be defined 毎年の定数でのlot_idの切り出し

    # listBの各要素で指定された数だけlistAから要素を切り出して
    # 新しいリストlistCを作成

    listA = S_one_list  # 5年分のlot_idリスト

    listB = year_lots_list  # 毎年毎の総ロット数

    listC = []  # 毎年のlot_idリスト

    start_idx = 0

    for i, num in enumerate(listB):

        end_idx = start_idx + num

        # original sample
        # listC.append(listA[start_idx:end_idx])

        # **********************************
        # "slice" and "allocate" at once
        # **********************************
        sliced_lots = listA[start_idx:end_idx]

        # 毎週の生産枠は、year_average_lots_listの平均値を取得する。
        N = year_average_lots_list[i]

        if N == 0:

            pass

        else:

            # その年の週次の出荷予定数が生成される。
            S_alloc_a_year = [
                sliced_lots[j : j + N] for j in range(0, len(sliced_lots), N)
            ]

            S_allocated.extend(S_alloc_a_year)
            # S_allocated.append(S_alloc_a_year)

        start_idx = end_idx

    ## 結果表示
    # print("S_allocated", S_allocated)

    # set psi on outbound supply

    # "JPN-OUT"
    #


    # ***********************************************
    #@241113 CHANGE root_node_outbound.psi4supplyが存在するという前提
    # ***********************************************
    #
    #node_name = root_node_outbound.name  # Nodeからnode_nameを取出す
    #
    ## for w, pSi in enumerate( S_allocated ):
    ##
    ##    node_psi_dict_Ot4Sp[node_name][w][0] = pSi
    

    # ***********************************************
    #@250628 MARK setting S_lots on "root supply" 4 PreProduction 
    # ***********************************************

    # 1. setting "pre_prod_S" on "root supply"   
    # "rice"demand[w][0]は平準化せずにそのままsupply[w][0]にセット
    #
    # <<NEXT ACTION>>
    # 2. calcS2P
    # 3. calcPSI

    #    self.root_node_outbound.calcS2P_4supply()
    #    self.root_node_outbound.calcPS2I4supply()




    for w in range(53 * plan_range):

        if w <= len(S_allocated) - 1:  # index=0 start

            root_node_outbound.psi4supply[w][0] = S_allocated[w]
            #node_psi_dict_Ot4Sp[node_name][w][0] = S_allocated[w]

        else:

            root_node_outbound.psi4supply[w][0] = []
            #node_psi_dict_Ot4Sp[node_name][w][0] = []

    # +++++++++++++++++++++++++++++++++++++++++++++++






def place_P_in_supply_LT(w, child, lot):  # lot LT_shift on P

    # *******************************************
    # supply_plan上で、PfixをSfixにPISでLT offsetする
    # *******************************************

    # **************************
    # Safety Stock as LT shift
    # **************************

    #@240925 STOP
    ## leadtimeとsafety_stock_weekは、ここでは同じ
    ## safety_stock_week = child.leadtime
    #LT_SS_week = child.leadtime


    #@240925 長期休暇がLT_SS_weekかchild.leadtimeかどちらにある場合は???

    #@240925
    # leadtimeとsafety_stock_weekは別もの
    LT_SS_week   = child.safety_stock_week
    LT_logi_week = child.leadtime



    # **************************
    # long vacation weeks
    # **************************
    lv_week = child.long_vacation_weeks

    ## P to S の計算処理
    # self.psi4supply = shiftP2S_LV(self.psi4supply, safety_stock_week, lv_week)

    ### S to P の計算処理
    ##self.psi4demand = shiftS2P_LV(self.psi4demand, safety_stock_week, lv_week)

    # my_list = [1, 2, 3, 4, 5]
    # for i in range(2, len(my_list)):
    #    my_list[i] = my_list[i-1] + my_list[i-2]

    # 0:S
    # 1:CO
    # 2:I
    # 3:P


    #@240925 STOP
    ## LT:leadtime SS:safty stockは1つ
    ## foreward planで、「親confirmed_S出荷=子confirmed_P着荷」と表現
    #eta_plan = w + LT_SS_week  # ETA=ETDなので、+LTすると次のETAとなる


    # LT_logi_weekで子nodeまでの物流LTを考慮
    eta_plan = w + LT_logi_week


    # etd_plan = w + ss # ss:safty stock
    # eta_plan = w - ss # ss:safty stock

    # *********************
    # 着荷週が事業所nodeの非稼働週の場合 +1次週の着荷とする
    # *********************
    # 着荷週を調整
    eta_shift = check_lv_week_fw(lv_week, eta_plan)  # ETA:Eatimate Time Arriv

    # リスト追加 extend
    # 安全在庫とカレンダ制約を考慮した着荷予定週Pに、w週Sからoffsetする

    # lot by lot operation
    # confirmed_P made by shifting parent_conf_S

    # ***********************
    # place_lot_supply_plan
    # ***********************

    # ここは、"REPLACE lot"するので、appendの前にchild psiをzero clearしてから

    #@240925 STOP
    ## 今回のmodelでは、輸送工程もpsi nodeと同等に扱っている(=POではない)ので
    ## 親のconfSを「そのままのWで」子のconfPに置く place_lotする
    #child.psi4supply[w][3].append(lot)

    ## 親のconfSを「eta_shiftしたWで」子のconfPに置く place_lotする
    # 親のconfSを「LT=輸送LT + 加工LT + SSでwをshiftして」子confSにplace_lot

    child.psi4supply[eta_shift][3].append(lot)

    # print("len(child.psi4supply)", len(child.psi4supply) ) # len() of psi list    # print("lot child.name eta_shift ",lot,  child.name, eta_shift )  # LT shift weeks


    # Sは、SS在庫分の後に出荷する
    ship_position = eta_shift + LT_SS_week

    # 出荷週を調整
    ship_shift = check_lv_week_fw(lv_week, ship_position) 

    child.psi4supply[ship_shift][0].append(lot)




def find_path_to_leaf_with_parent(node, leaf_node, current_path=[]):

    current_path.append(leaf_node.name)

    if node.name == leaf_node.name:

        return current_path

    else:

        parent = leaf_node.parent

        path = find_path_to_leaf_with_parent(node, parent, current_path.copy())

    return path


#        if path:
#
#            return path


def extract_node_name(stringA):
    """
    Extract the node name from a string by removing the last 9 characters (YYYYWWNNN).

    Parameters:
        stringA (str): Input string (e.g., "LEAF01202601001").

    Returns:
        str: Node name (e.g., "LEAF01").
    """
    if len(stringA) > 10:
        # 最後の10文字を削除して返す #deep relation on "def generate_lot_ids()"
        return stringA[:-10]
    else:
        # 文字列が10文字以下の場合、削除せずそのまま返す（安全策）
        return stringA


#lot_IDが3桁の場合{i+1:03d}に、 9文字を削る
#lot_IDが4桁の場合{i+1:04d}に、10文字を削る
#10文字は、lot_IDが3桁の場合{i+1:03d}
#
# following "def generate_lot_ids()" is in "demand_generate.py"
#def generate_lot_ids(row):
#    """
#    Generate lot IDs based on the row's data.
#
#    Parameters:
#        row (pd.Series): A row from the DataFrame.
#
#    Returns:
#        list: List of generated lot IDs.
#    """
#    lot_count = row["S_lot"]
#
#    return [f"{row['node_name']}{row['iso_year']}{row['iso_week']}{i+1:03d}" for i in range(lot_count)]
#



def extract_node_name_OLD(stringA):
    # 右側の数字部分を除外してnode名を取得

    index = len(stringA) - 1

    while index >= 0 and stringA[index].isdigit():

        index -= 1

    node_name = stringA[: index + 1]

    return node_name





# ******************************************
# confirmedSを出荷先ship2のPとSにshift&set
# ******************************************

# 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
# main function is this: place_P_in_supply_LT(w, ship2node, lot)

def feedback_psi_lists(node, nodes):
#def feedback_psi_lists(node, node_psi_dict, nodes):

    # キーが存在する場合は対応する値valueが返り、存在しない場合はNoneが返る。

    if node.children == []:  # 子nodeがないleaf nodeの場合

        pass

    else:

        # ************************************
        # clearing children P[w][3] and S[w][0]
        # ************************************
        # replace lotするために、事前に、
        # 出荷先となるすべてのchildren nodesのS[w][0]とP[w][3]をクリア

        for child in node.children:

            for w in range(53 * node.plan_range):

                child.psi4supply[w][0] = []
                child.psi4supply[w][3] = []

        # lotidから、leaf_nodeを特定し、出荷先ship2nodeに出荷することは、
        # すべての子nodeに出荷することになる

        # ************************************
        # setting mother_confirmed_S
        # ************************************
        # このnode内での子nodeへの展開
        for w in range(53 * node.plan_range):

            #@STOP
            #print("node.psi4supply", node.psi4supply)

            confirmed_S_lots = node.psi4supply[w][0]  # 親の確定出荷confS lot

            print("confirmed_S_lots", confirmed_S_lots)

            # 出荷先nodeを特定して

            # 一般には、下記のLT shiftだが・・・・・
            # 出荷先の ETA = LT_shift(ETD) でP place_lot
            # 工程中の ETA = SS_shift(ETD) でS place_lot

            # 本モデルでは、輸送工程 = modal_nodeを想定して・・・・・
            # 出荷先の ETA = 出荷元ETD        でP place_lot
            # 工程中の ETA = LT&SS_shift(ETD) でS place_lot
            # というイビツなモデル定義・・・・・

            # 直感的なPO=INVOICEという考え方に戻すべきかも・・・・・
            #
            # modal shiftのmodelingをLT_shiftとの拡張で考える???
            # modal = BOAT/AIR/QURIE
            # LT_shift(modal, w, ,,,,

            for lot in confirmed_S_lots:

                if lot == []:

                    pass

                else:

                    # *********************************************************
                    # child#ship2node = find_node_to_ship(node, lot)
                    # lotidからleaf_nodeのpointerを返す

                    print("lot_ID", lot)

                    leaf_node_name = extract_node_name(lot)

                    print("lot_ID leaf_node_name", lot, leaf_node_name )


                    leaf_node = nodes[leaf_node_name]



                    # 末端からあるnodeAまでleaf_nodeまでのnode_listをpathで返す

                    current_path = []
                    path = []

                    path = find_path_to_leaf_with_parent(node, leaf_node, current_path)

                    # nodes_listを逆にひっくり返す
                    path.reverse()

                    # 出荷先nodeはnodeAの次node、path[1]になる
                    ship2node_name = path[1]

                    ship2node = nodes[ship2node_name]

                    # ここでsupply planを更新している

                    # lot: 親nodeの確定出荷confirmed_S lotsを
                    # ship2node: 子nodeの出荷先を(lot_IDから)特定してある

                    # 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
                    place_P_in_supply_LT(w, ship2node, lot)

    for child in node.children:

        feedback_psi_lists(child, nodes)
        #feedback_psi_lists(child, node_psi_dict, nodes)






def copy_P_demand2supply(node): # TOBE 240926
#def update_child_PS(node): # TOBE 240926

    # 明示的に.copyする。
    plan_len = 53 * node.plan_range
    for w in range(0, plan_len):

        node.psi4supply[w][3] = node.psi4demand[w][3].copy()



def PULL_process(node):
    # *******************************************
    # decouple nodeは、pull_Sで出荷指示する
    # *******************************************

    #@241002 childで、親nodeの確定S=確定P=demandのPで計算済み
    # copy S&P demand2supply for PULL
    copy_S_demand2supply(node)
    copy_P_demand2supply(node)


    # 自分のnodeをPS2Iで確定する
    node.calcPS2I4supply()  # calc_psi with PULL_S&P

    print(f"PULL_process applied to {node.name}")



def apply_pull_process(node):

    #@241002 MOVE
    #PULL_process(node)

    for child in node.children:


        PULL_process(child)


        apply_pull_process(child)




def copy_S_demand2supply(node): # TOBE 240926
#def update_child_PS(node): # TOBE 240926

    # 明示的に.copyする。
    plan_len = 53 * node.plan_range
    for w in range(0, plan_len):

        node.psi4supply[w][0] = node.psi4demand[w][0].copy()




def PUSH_process(node):


    # ***************
    # decoupl nodeに入って最初にcalcPS2Iで状態を整える
    # ***************
    node.calcPS2I4supply()  # calc_psi with PULL_S


    # STOP STOP
    ##@241002 decoupling nodeのみpullSで確定ship
    ## *******************************************
    ## decouple nodeは、pull_Sで出荷指示する
    ## *******************************************
    ## copy S demand2supply
    #copy_S_demand2supply(node)
    #
    ## 自分のnodeをPS2Iで確定する
    #node.calcPS2I4supply()  # calc_psi with PUSH_S


    print(f"PUSH_process applied to {node.name}")





def push_pull_all_psi2i_decouple4supply5(node, decouple_nodes):


    print("node in supply_proc", node.name )

    if  node.name == "DADJPN":
        print("DADJPN.psi4demand", node.psi4demand )
        print("DADJPN.psi4supply", node.psi4supply )
    

    if node.name in decouple_nodes:

        # ***************
        # decoupl nodeに入って最初にcalcPS2Iで状態を整える
        # ***************
        node.calcPS2I4supply()  # calc_psi with PULL_S


        #@241002 decoupling nodeのみpullSで確定ship
        # *******************************************
        # decouple nodeは、pull_Sで出荷指示する
        # *******************************************
        copy_S_demand2supply(node)

        PUSH_process(node)         # supply SP2Iしてからの

        apply_pull_process(node)   # demandSに切り替え

    else:

        PUSH_process(node)

        for child in node.children:

            push_pull_all_psi2i_decouple4supply5(child, decouple_nodes)





def map_psi_lots2df(node, D_S_flag, psi_lots):
    if D_S_flag == "demand":
        matrix = node.psi4demand
    elif D_S_flag == "supply":
        matrix = node.psi4supply
    else:
        print("error: wrong D_S_flag is defined")
        return pd.DataFrame()

    for week, row in enumerate(matrix):
        for scoip, lots in enumerate(row):
            for step_no, lot_id in enumerate(lots):
                psi_lots.append([node.name, week, scoip, step_no, lot_id])

    for child in node.children:
        map_psi_lots2df(child, D_S_flag, psi_lots)

    columns = ["node_name", "week", "s-co-i-p", "step_no", "lot_id"]
    df = pd.DataFrame(psi_lots, columns=columns)
    return df





# **************************
# collect_psi_data
# **************************


def collect_psi_data(node, D_S_flag, week_start, week_end, psi_data):
    if D_S_flag not in ["demand", "supply"]:
        print("error: D_S_flag should be 'demand' or 'supply'")
        return

    psi_lots = []
    df_plan = map_psi_lots2df(node, D_S_flag, psi_lots)

    if df_plan.empty:
        print(f"[{node.name}] No data for PSI ({D_S_flag})")
        return

    # week_end の範囲を調整（データ内最大weekに合わせる）
    max_week = df_plan["week"].max()
    week_end = min(week_end, max_week)

    df_filtered = df_plan[
        (df_plan["node_name"] == node.name) &
        (df_plan["week"] >= week_start) &
        (df_plan["week"] <= week_end)
    ]

    print(f"[{node.name}] PSI df shape: {df_filtered.shape}")
    print(df_filtered[df_filtered["s-co-i-p"] == 3].head())  # P
    print(df_filtered[df_filtered["s-co-i-p"] == 2].head())  # I
    print(df_filtered[df_filtered["s-co-i-p"] == 0].head())  # S

    # 分割＆集計
    line_data_2I = df_filtered[df_filtered["s-co-i-p"] == 2]
    bar_data_0S = df_filtered[df_filtered["s-co-i-p"] == 0]
    bar_data_3P = df_filtered[df_filtered["s-co-i-p"] == 3]

    line_plot_data_2I = line_data_2I.groupby("week")["lot_id"].count()
    bar_plot_data_3P = bar_data_3P.groupby("week")["lot_id"].count()
    bar_plot_data_0S = bar_data_0S.groupby("week")["lot_id"].count()

    # インデックスはintに（描画エラー防止）
    line_plot_data_2I.index = line_plot_data_2I.index.astype(int)
    bar_plot_data_3P.index = bar_plot_data_3P.index.astype(int)
    bar_plot_data_0S.index = bar_plot_data_0S.index.astype(int)

    # 指標評価
    revenue = round(getattr(node, "eval_cs_price_sales_shipped", 0))
    profit = round(getattr(node, "eval_cs_profit", 0))
    profit_ratio = round((profit / revenue) * 100, 1) if revenue != 0 else 0

    psi_data.append((
        node.name, revenue, profit, profit_ratio,
        line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S
    ))



def collect_psi_data_OLD2507032127(node, D_S_flag, week_start, week_end, psi_data):
    if D_S_flag == "demand":
        psi_lots = []
        df_demand_plan = map_psi_lots2df(node, D_S_flag, psi_lots)
        df_init = df_demand_plan
    elif D_S_flag == "supply":
        psi_lots = []
        df_supply_plan = map_psi_lots2df(node, D_S_flag, psi_lots)
        df_init = df_supply_plan
    else:
        print("error: D_S_flag should be demand or supply")
        return

    # 修正：week_end の範囲超え防止
    if not df_init.empty:
        max_week = df_init["week"].max()
        week_end = min(week_end, max_week)

    condition1 = df_init["node_name"] == node.name
    condition2 = (df_init["week"] >= week_start) & (df_init["week"] <= week_end)
    df = df_init[condition1 & condition2]

    # デバッグ用 print（必要なら）
    print(f"[{node.name}] PSI df shape: {df.shape}")
    print(df[df["s-co-i-p"] == 3].head())  # P
    print(df[df["s-co-i-p"] == 2].head())  # I
    print(df[df["s-co-i-p"] == 0].head())  # S

    line_data_2I = df[df["s-co-i-p"].isin([2])]
    bar_data_0S = df[df["s-co-i-p"] == 0]
    bar_data_3P = df[df["s-co-i-p"] == 3]

    line_plot_data_2I = line_data_2I.groupby("week")["lot_id"].count()
    bar_plot_data_3P = bar_data_3P.groupby("week")["lot_id"].count()
    bar_plot_data_0S = bar_data_0S.groupby("week")["lot_id"].count()

    revenue = round(node.eval_cs_price_sales_shipped)
    profit = round(node.eval_cs_profit)
    profit_ratio = round((profit / revenue) * 100, 1) if revenue != 0 else 0

    psi_data.append((node.name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S))


def collect_psi_data_OLD250630(node, D_S_flag, week_start, week_end, psi_data):
    if D_S_flag == "demand":
        psi_lots = []
        df_demand_plan = map_psi_lots2df(node, D_S_flag, psi_lots)
        df_init = df_demand_plan
    elif D_S_flag == "supply":
        psi_lots = []
        df_supply_plan = map_psi_lots2df(node, D_S_flag, psi_lots)
        df_init = df_supply_plan
    else:
        print("error: D_S_flag should be demand or supply")
        return

    condition1 = df_init["node_name"] == node.name
    condition2 = (df_init["week"] >= week_start) & (df_init["week"] <= week_end)
    df = df_init[condition1 & condition2]

    line_data_2I = df[df["s-co-i-p"].isin([2])]
    bar_data_0S = df[df["s-co-i-p"] == 0]
    bar_data_3P = df[df["s-co-i-p"] == 3]

    line_plot_data_2I = line_data_2I.groupby("week")["lot_id"].count()
    bar_plot_data_3P = bar_data_3P.groupby("week")["lot_id"].count()
    bar_plot_data_0S = bar_data_0S.groupby("week")["lot_id"].count()



    # ノードのREVENUEとPROFITを四捨五入

    # root_out_optからroot_outboundの世界へ変換する
    #@241225 be checked

    #@ STOP
    ##@ TEST node_optとnode_originに、revenueとprofit属性を追加
    #revenue = round(node.revenue)
    #profit  = round(node.profit)


    #@241225 STOP "self.nodes_outbound"がscopeにない
    #node_origin = self.nodes_outbound[node.name]
    #

    revenue = round(node.eval_cs_price_sales_shipped)
    profit = round(node.eval_cs_profit)



    # PROFIT_RATIOを計算して四捨五入
    profit_ratio = round((profit / revenue) * 100, 1) if revenue != 0 else 0

    psi_data.append((node.name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S))




# node is "node_opt"
def collect_psi_data_opt(node, node_out, D_S_flag, week_start, week_end, psi_data):
    if D_S_flag == "demand":
        psi_lots = []
        df_demand_plan = map_psi_lots2df(node, D_S_flag, psi_lots)
        df_init = df_demand_plan
    elif D_S_flag == "supply":
        psi_lots = []
        df_supply_plan = map_psi_lots2df(node, D_S_flag, psi_lots)
        df_init = df_supply_plan
    else:
        print("error: D_S_flag should be demand or supply")
        return

    condition1 = df_init["node_name"] == node.name
    condition2 = (df_init["week"] >= week_start) & (df_init["week"] <= week_end)
    df = df_init[condition1 & condition2]

    line_data_2I = df[df["s-co-i-p"].isin([2])]
    bar_data_0S = df[df["s-co-i-p"] == 0]
    bar_data_3P = df[df["s-co-i-p"] == 3]

    line_plot_data_2I = line_data_2I.groupby("week")["lot_id"].count()
    bar_plot_data_3P = bar_data_3P.groupby("week")["lot_id"].count()
    bar_plot_data_0S = bar_data_0S.groupby("week")["lot_id"].count()



    # ノードのREVENUEとPROFITを四捨五入

    # root_out_optからroot_outboundの世界へ変換する
    #@241225 be checked

    #@ STOP
    ##@ TEST node_optとnode_originに、revenueとprofit属性を追加
    #revenue = round(node.revenue)
    #profit  = round(node.profit)


    #@241225 STOP "self.nodes_outbound"がscopeにない
    #node_origin = self.nodes_outbound[node.name]
    #

    # nodeをoptからoutに切り替え
    revenue = round(node_out.eval_cs_price_sales_shipped)
    profit = round(node_out.eval_cs_profit)



    # PROFIT_RATIOを計算して四捨五入
    profit_ratio = round((profit / revenue) * 100, 1) if revenue != 0 else 0

    psi_data.append((node.name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S))




#@250110 STOP
## gui/app.py
#class PSIPlannerApp:
#    def __init__(self, root, config):
#        self.root = root
#        self.config = config
#        self.root.title(self.config.APP_NAME)
#
#        self.tree_structure = None
#
#        # 必ず setup_ui を先に呼び出す
#        self.setup_ui()
#        
#        # 必要な初期化処理を後から呼び出す
#        self.initialize_parameters()
#
#
#
#        # PSI planner
#        self.outbound_data = None
#        self.inbound_data = None
#
#        self.root_node_outbound = None
#        self.nodes_outbound = None
#        self.leaf_nodes_out = []
#
#        self.root_node_inbound = None
#        self.nodes_inbound = None
#        self.leaf_nodes_in = []
#
#        self.total_revenue = 0
#        self.total_profit = 0
#        self.profit_ratio = 0
#
#        # View settings
#        self.G = None
#        self.pos_E2E = None
#        self.fig_network = None
#        self.ax_network = None
#
#        # Initialize parameters
#        self.initialize_parameters()




def is_picklable(value):
    try:
        pickle.dumps(value)
    except (pickle.PicklingError, TypeError):
        return False
    return True





class PSIPlannerApp4save:

    #def __init__(self, root):

    def __init__(self):

        #self.root = root
        #self.root.title("Global Weekly PSI Planner")

        self.root_node = None  # root_nodeの定義を追加


        self.lot_size     = 2000      # 初期値

        self.plan_year_st = 2022      # 初期値
        self.plan_range   = 2         # 初期値

        self.pre_proc_LT  = 13        # 初期値 13week = 3month


        self.market_potential = 0     # 初期値 0
        self.target_share     = 0.5   # 初期値 0.5 = 50%
        self.total_supply     = 0     # 初期値 0


        #@ STOP
        #self.setup_ui()

        self.outbound_data = None
        self.inbound_data = None

        # PySI tree
        self.root_node_outbound = None
        self.nodes_outbound     = None
        self.leaf_nodes_out     = []

        self.root_node_inbound  = None
        self.nodes_inbound      = None
        self.leaf_nodes_in      = []

        self.root_node_out_opt  = None
        self.nodes_out_opt      = None
        self.leaf_nodes_opt     = []


        self.optimized_root     = None
        self.optimized_nodes    = None


        # Evaluation on PSI
        self.total_revenue = 0
        self.total_profit  = 0
        self.profit_ratio  = 0


        # view
        self.G = None

        # Optimise
        self.Gdm_structure = None

        self.Gdm = None
        self.Gsp = None

        self.pos_E2E = None

        self.flowDict_opt = {} #None
        self.flowCost_opt = {} #None

        self.total_supply_plan = 0

        # loading files
        self.directory = None
        self.load_directory = None

        self.base_leaf_name = None

        # supply_plan / decoupling / buffer stock
        self.decouple_node_dic = {}

        self.decouple_node_selected = []



    #@ STOP
    #def update_from_psiplannerapp(self, psi_planner_app):
    #    self.__dict__.update(psi_planner_app.__dict__)
    #
    #def update_psiplannerapp(self, psi_planner_app):
    #    psi_planner_app.__dict__.update(self.__dict__)



#@ STOP
#    def update_from_psiplannerapp(self, psi_planner_app):
#        attributes = {key: value for key, value in psi_planner_app.__dict__.items() if key != 'root'}
#        self.__dict__.update(attributes)
#
#    def update_psiplannerapp(self, psi_planner_app):
#        attributes = {key: value for key, value in self.__dict__.items()}
#        psi_planner_app.__dict__.update(attributes)







    def update_from_psiplannerapp(self, psi_planner_app):
        attributes = {key: value for key, value in psi_planner_app.__dict__.items()
                      if key != 'root' and is_picklable(value) and not isinstance(value, (tk.Tk, tk.Widget, tk.Toplevel, tk.Variable))}
        self.__dict__.update(attributes)

    def update_psiplannerapp(self, psi_planner_app):
        attributes = {key: value for key, value in self.__dict__.items()}
        psi_planner_app.__dict__.update(attributes)




# **************************
# cost_stracture
# **************************





def make_stack_bar4cost_stracture(cost_dict):
    attributes_B = [
        'cs_direct_materials_costs',
        'cs_marketing_promotion',
        'cs_sales_admin_cost',
        'cs_tax_portion',
        'cs_logistics_costs',
        'cs_warehouse_cost',
        'cs_prod_indirect_labor',
        'cs_prod_indirect_others',
        'cs_direct_labor_costs',
        'cs_depreciation_others',
        'cs_profit',
    ]

    colors = {
        'cs_direct_materials_costs': 'lightgray',
        'cs_marketing_promotion': 'darkblue',
        'cs_sales_admin_cost': 'blue',
        'cs_tax_portion': 'gray',
        'cs_logistics_costs': 'cyan',
        'cs_warehouse_cost': 'magenta',
        'cs_prod_indirect_labor': 'green',
        'cs_prod_indirect_others': 'lightgreen',
        'cs_direct_labor_costs': 'limegreen',
        'cs_depreciation_others': 'yellowgreen',
        'cs_profit': 'gold',
    }

    nodes = list(cost_dict.keys())
    bar_width = 0.3  

    plt.close('all')  # 🔴【追加】過去のグラフをすべて閉じる

    # 画面サイズを取得 (PCの解像度)
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()

    # 縦2つに並べるためのウィンドウサイズ (フルサイズの半分)
    win_width = screen_width
    win_height = screen_height // 2  

    # 🔴【修正】ウィンドウサイズを大きく
    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)  

    # 🔴【修正】bottoms を適切に初期化 (ゼロ配列)
    bottoms = np.zeros(len(nodes))

    for attr in attributes_B:
        values = [cost_dict[node][attr] for node in cost_dict]
        ax.bar(nodes, values, bar_width, label=attr, color=colors[attr], bottom=bottoms)
        bottoms += values  

        # Add text on bars
        for i, value in enumerate(values):
            if value > 0:
                ax.text(i, bottoms[i] - value / 2, f'{value:.1f}', ha='center', va='center', fontsize=6, color='black')

    # Add total values on top of bars
    total_values = [sum(cost_dict[node][attr] for attr in attributes_B) for node in cost_dict]
    for i, total in enumerate(total_values):
        ax.text(i, total + 2, f'{total:.1f}', ha='center', va='bottom', fontsize=6)

    ax.set_title('Supply Chain Cost Structure', fontsize=10)  
    ax.set_xlabel('Node', fontsize=8)  
    ax.set_ylabel('Amount', fontsize=8)

    # 凡例を左上に配置
    ax.legend(title='Attribute', fontsize=6, loc='upper left')

    # X軸ラベルを回転
    ax.set_xticks(range(len(nodes)))
    ax.set_xticklabels(nodes, rotation=30, fontsize=7)  

    # 余白調整
    fig.subplots_adjust(left=0.2, right=0.85, top=0.9, bottom=0.3)

    # 🔴【修正】ウィンドウを画面下半分に移動
    mng = plt.get_current_fig_manager()
    
    #try:
    #    # Windows/macOS (TkAgg)
    #    mng.window.geometry(f"{win_width}x{win_height}+0+{win_height}")  
    #except AttributeError:
    #    # Linux (Qt5Agg)
    #    mng.window.setGeometry(0, win_height, win_width, win_height)




    plt.show()



#import matplotlib.pyplot as plt
#import numpy as np
#import tkinter as tk



#@250325
## Add text on bars
#for i, value in enumerate(values):
#    if value > 0:
#        ax.text(i, bottoms[i] - value / 2, f'{value:.1f}', ha='center', va='center', fontsize=6, color='black')  # 色を黒に変更






def make_stack_bar4cost_stracture_OLD6(cost_dict):
    attributes_B = [
        'cs_direct_materials_costs',
        'cs_marketing_promotion',
        'cs_sales_admin_cost',
        'cs_tax_portion',
        'cs_logistics_costs',
        'cs_warehouse_cost',
        'cs_prod_indirect_labor',
        'cs_prod_indirect_others',
        'cs_direct_labor_costs',
        'cs_depreciation_others',
        'cs_profit',
    ]

    colors = {
        'cs_direct_materials_costs': 'lightgray',
        'cs_marketing_promotion': 'darkblue',
        'cs_sales_admin_cost': 'blue',
        'cs_tax_portion': 'gray',
        'cs_logistics_costs': 'cyan',
        'cs_warehouse_cost': 'magenta',
        'cs_prod_indirect_labor': 'green',
        'cs_prod_indirect_others': 'lightgreen',
        'cs_direct_labor_costs': 'limegreen',
        'cs_depreciation_others': 'yellowgreen',
        'cs_profit': 'gold',
    }

    nodes = list(cost_dict.keys())
    bar_width = 0.3  

    plt.close('all')  # 🔴【追加】過去のグラフをすべて閉じる

    # 画面サイズを取得 (PCの解像度)
    root = tk.Tk()
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.destroy()

    # 縦2つに並べるためのウィンドウサイズ (フルサイズの半分)
    win_width = screen_width
    win_height = screen_height // 2  

    # 🔴【修正】ウィンドウサイズを大きく
    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)  

    for attr in attributes_B:
        values = [cost_dict[node][attr] for node in cost_dict]
        ax.bar(nodes, values, bar_width, label=attr, color=colors[attr], bottom=bottoms)
        bottoms += values  

        # Add text on bars
        for i, value in enumerate(values):
            if value > 0:
                ax.text(i, bottoms[i] - value / 2, f'{value:.1f}', ha='center', va='center', fontsize=6, color='black')

    # Add total values on top of bars
    total_values = [sum(cost_dict[node][attr] for attr in attributes_B) for node in cost_dict]
    for i, total in enumerate(total_values):
        ax.text(i, total + 2, f'{total:.1f}', ha='center', va='bottom', fontsize=6)

    ax.set_title('Supply Chain Cost Structure', fontsize=10)  
    ax.set_xlabel('Node', fontsize=8)  
    ax.set_ylabel('Amount', fontsize=8)

    # 凡例を左上に配置
    ax.legend(title='Attribute', fontsize=6, loc='upper left')

    # X軸ラベルを回転
    ax.set_xticks(range(len(nodes)))
    ax.set_xticklabels(nodes, rotation=30, fontsize=7)  

    # 余白調整
    fig.subplots_adjust(left=0.2, right=0.85, top=0.9, bottom=0.3)

    # 🔴【追加】ウィンドウ位置を指定 (画面の下半分に表示)
    mng = plt.get_current_fig_manager()
    mng.window.geometry(f"{win_width}x{win_height}+0+{win_height}")  # (横幅)x(縦幅)+(X座標)+(Y座標)

    plt.show()



def make_stack_bar4cost_stracture_OLD5(cost_dict):
    attributes_B = [
        'cs_direct_materials_costs',
        'cs_marketing_promotion',
        'cs_sales_admin_cost',
        'cs_tax_portion',
        'cs_logistics_costs',
        'cs_warehouse_cost',
        'cs_prod_indirect_labor',
        'cs_prod_indirect_others',
        'cs_direct_labor_costs',
        'cs_depreciation_others',
        'cs_profit',
    ]

    colors = {
        'cs_direct_materials_costs': 'lightgray',
        'cs_marketing_promotion': 'darkblue',
        'cs_sales_admin_cost': 'blue',
        'cs_tax_portion': 'gray',
        'cs_logistics_costs': 'cyan',
        'cs_warehouse_cost': 'magenta',
        'cs_prod_indirect_labor': 'green',
        'cs_prod_indirect_others': 'lightgreen',
        'cs_direct_labor_costs': 'limegreen',
        'cs_depreciation_others': 'yellowgreen',
        'cs_profit': 'gold',
    }

    nodes = list(cost_dict.keys())
    bar_width = 0.3  

    plt.close('all')  # 🔴【追加】過去のグラフをすべて閉じる

    # Initialize the bottom of the bars
    bottoms = np.zeros(len(nodes))

    fig, ax = plt.subplots(figsize=(12, 6), dpi=100)  
    #fig, ax = plt.subplots(figsize=(6, 3), dpi=100)  

    for attr in attributes_B:
        values = [cost_dict[node][attr] for node in cost_dict]
        ax.bar(nodes, values, bar_width, label=attr, color=colors[attr], bottom=bottoms)
        bottoms += values  

        # Add text on bars
        for i, value in enumerate(values):
            if value > 0:
                ax.text(i, bottoms[i] - value / 2, f'{value:.1f}', ha='center', va='center', fontsize=6, color='white')

    # Add total values on top of bars
    total_values = [sum(cost_dict[node][attr] for attr in attributes_B) for node in cost_dict]
    for i, total in enumerate(total_values):
        ax.text(i, total + 2, f'{total:.1f}', ha='center', va='bottom', fontsize=6)

    ax.set_title('Supply Chain Cost Structure', fontsize=10)  
    ax.set_xlabel('Node', fontsize=8)  
    ax.set_ylabel('Amount', fontsize=8)

    # 🔴【修正】凡例を左上に配置
    ax.legend(title='Attribute', fontsize=6, loc='upper left')

    # X軸ラベルを回転
    ax.set_xticks(range(len(nodes)))
    ax.set_xticklabels(nodes, rotation=30, fontsize=7)  

    # 余白調整
    fig.subplots_adjust(left=0.2, right=0.85, top=0.9, bottom=0.3)

    plt.show()



def make_stack_bar4cost_stracture_OLD4(cost_dict):
    attributes_B = [
        'cs_direct_materials_costs',
        'cs_marketing_promotion',
        'cs_sales_admin_cost',
        'cs_tax_portion',
        'cs_logistics_costs',
        'cs_warehouse_cost',
        'cs_prod_indirect_labor',
        'cs_prod_indirect_others',
        'cs_direct_labor_costs',
        'cs_depreciation_others',
        'cs_profit',
    ]

    colors = {
        'cs_direct_materials_costs': 'lightgray',
        'cs_marketing_promotion': 'darkblue',
        'cs_sales_admin_cost': 'blue',
        'cs_tax_portion': 'gray',
        'cs_logistics_costs': 'cyan',
        'cs_warehouse_cost': 'magenta',
        'cs_prod_indirect_labor': 'green',
        'cs_prod_indirect_others': 'lightgreen',
        'cs_direct_labor_costs': 'limegreen',
        'cs_depreciation_others': 'yellowgreen',
        'cs_profit': 'gold',
    }

    nodes = list(cost_dict.keys())
    bar_width = 0.3  

    # 🔴【追加】過去のグラフをすべて閉じる
    plt.close('all') 

    # Initialize the bottom of the bars
    bottoms = np.zeros(len(nodes))

    # 🔴【修正】新しいグラフを作成
    fig, ax = plt.subplots(figsize=(6, 3), dpi=100)  

    for attr in attributes_B:
        values = [cost_dict[node][attr] for node in cost_dict]
        ax.bar(nodes, values, bar_width, label=attr, color=colors[attr], bottom=bottoms)
        bottoms += values  

        # Add text on bars
        for i, value in enumerate(values):
            if value > 0:
                ax.text(i, bottoms[i] - value / 2, f'{value:.1f}', ha='center', va='center', fontsize=6, color='white')

    # Add total values on top of bars
    total_values = [sum(cost_dict[node][attr] for attr in attributes_B) for node in cost_dict]
    for i, total in enumerate(total_values):
        ax.text(i, total + 2, f'{total:.1f}', ha='center', va='bottom', fontsize=6)

    ax.set_title('Supply Chain Cost Structure', fontsize=10)  
    ax.set_xlabel('Node', fontsize=8)  
    ax.set_ylabel('Amount', fontsize=8)

    # 凡例を小さめに
    ax.legend(title='Attribute', fontsize=6, loc='upper right')

    # X軸ラベルを回転
    ax.set_xticks(range(len(nodes)))
    ax.set_xticklabels(nodes, rotation=30, fontsize=7)  

    # 余白調整
    fig.subplots_adjust(left=0.2, right=0.85, top=0.9, bottom=0.3)

    # 🔴【修正】グラフを表示
    plt.show()




def make_stack_bar4cost_stracture_OLD3(cost_dict):
    attributes_B = [
        'cs_direct_materials_costs',
        'cs_marketing_promotion',
        'cs_sales_admin_cost',
        'cs_tax_portion',
        'cs_logistics_costs',
        'cs_warehouse_cost',
        'cs_prod_indirect_labor',
        'cs_prod_indirect_others',
        'cs_direct_labor_costs',
        'cs_depreciation_others',
        'cs_profit',
    ]

    colors = {
        'cs_direct_materials_costs': 'lightgray',
        'cs_marketing_promotion': 'darkblue',
        'cs_sales_admin_cost': 'blue',
        'cs_tax_portion': 'gray',
        'cs_logistics_costs': 'cyan',
        'cs_warehouse_cost': 'magenta',
        'cs_prod_indirect_labor': 'green',
        'cs_prod_indirect_others': 'lightgreen',
        'cs_direct_labor_costs': 'limegreen',
        'cs_depreciation_others': 'yellowgreen',
        'cs_profit': 'gold',
    }

    nodes = list(cost_dict.keys())
    bar_width = 0.3  # 棒の幅を細くする

    # Initialize the bottom of the bars
    bottoms = np.zeros(len(nodes))

    # 🔴 【修正1】figsize を小さく、dpi を設定
    fig, ax = plt.subplots(figsize=(6, 3), dpi=100)  

    for attr in attributes_B:
        values = [cost_dict[node][attr] for node in cost_dict]
        ax.bar(nodes, values, bar_width, label=attr, color=colors[attr], bottom=bottoms)
        bottoms += values

        # Add text on bars (フォントサイズを小さく)
        for i, value in enumerate(values):
            if value > 0:
                ax.text(i, bottoms[i] - value / 2, f'{value:.1f}', ha='center', va='center', fontsize=6, color='white')

    # Add total values on top of bars
    total_values = [sum(cost_dict[node][attr] for attr in attributes_B) for node in cost_dict]
    for i, total in enumerate(total_values):
        ax.text(i, total + 2, f'{total:.1f}', ha='center', va='bottom', fontsize=6)  # フォント小さめ

    ax.set_title('Supply Chain Cost Structure', fontsize=10)  # タイトル小さめ
    ax.set_xlabel('Node', fontsize=8)  # 軸ラベル小さめ
    ax.set_ylabel('Amount', fontsize=8)

    # 🔴 【修正2】凡例を小さめに
    ax.legend(title='Attribute', fontsize=6, loc='upper right')

    # 🔴 【修正3】X軸ラベルを小さく＆回転
    ax.set_xticks(range(len(nodes)))
    ax.set_xticklabels(nodes, rotation=30, fontsize=7)  # 30度回転して省スペース

    # 🔴 【修正4】はみ出し防止のための余白調整
    fig.subplots_adjust(left=0.2, right=0.85, top=0.9, bottom=0.3)

    plt.show()




def make_stack_bar4cost_stracture_OLD2(cost_dict):
    attributes_B = [
        'cs_direct_materials_costs',
        'cs_marketing_promotion',
        'cs_sales_admin_cost',
        'cs_tax_portion',
        'cs_logistics_costs',
        'cs_warehouse_cost',
        'cs_prod_indirect_labor',
        'cs_prod_indirect_others',
        'cs_direct_labor_costs',
        'cs_depreciation_others',
        'cs_profit',
    ]

    colors = {
        'cs_direct_materials_costs': 'lightgray',
        'cs_marketing_promotion': 'darkblue',
        'cs_sales_admin_cost': 'blue',
        'cs_tax_portion': 'gray',
        'cs_logistics_costs': 'cyan',
        'cs_warehouse_cost': 'magenta',
        'cs_prod_indirect_labor': 'green',
        'cs_prod_indirect_others': 'lightgreen',
        'cs_direct_labor_costs': 'limegreen',
        'cs_depreciation_others': 'yellowgreen',
        'cs_profit': 'gold',
    }

    nodes = list(cost_dict.keys())
    bar_width = 0.5

    # Initialize the bottom of the bars
    bottoms = np.zeros(len(nodes))

    fig, ax = plt.subplots()

    for attr in attributes_B:
        values = [cost_dict[node][attr] for node in cost_dict]
        ax.bar(nodes, values, bar_width, label=attr, color=colors[attr], bottom=bottoms)
        bottoms += values

        # Add text on bars
        for i, value in enumerate(values):
            if value > 0:
                ax.text(i, bottoms[i] - value / 2, f'{value:.1f}', ha='center', va='center', fontsize=8, color='white')

    # Add total values on top of bars
    total_values = [sum(cost_dict[node][attr] for attr in attributes_B) for node in cost_dict]
    for i, total in enumerate(total_values):
        ax.text(i, total + 2, f'{total:.1f}', ha='center', va='bottom', fontsize=8)
        #ax.text(i, total + 2, f'{total:.1f}', ha='center', va='bottom', fontsize=10)

    ax.set_title('Supply Chain Cost Structure on Common Planning Unit')
    ax.set_xlabel('Node')
    ax.set_ylabel('Amount')

    # Set legend with smaller fontsize
    ax.legend(title='Attribute', fontsize=6 )
    #ax.legend(title='Attribute', fontsize='small')

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()




def make_stack_bar4cost_stracture_OLD(cost_dict):
    attributes_B = [
        'cs_direct_materials_costs',
        'cs_marketing_promotion',
        'cs_sales_admin_cost',
        'cs_tax_portion',
        'cs_logistics_costs',
        'cs_warehouse_cost',
        'cs_prod_indirect_labor',
        'cs_prod_indirect_others',
        'cs_direct_labor_costs',
        'cs_depreciation_others',
        'cs_profit',
    ]

    colors = {
        'cs_direct_materials_costs': 'lightgray',
        'cs_marketing_promotion': 'darkblue',
        'cs_sales_admin_cost': 'blue',
        'cs_tax_portion': 'gray',
        'cs_logistics_costs': 'cyan',
        'cs_warehouse_cost': 'magenta',
        'cs_prod_indirect_labor': 'green',
        'cs_prod_indirect_others': 'lightgreen',
        'cs_direct_labor_costs': 'limegreen',
        'cs_depreciation_others': 'yellowgreen',
        'cs_profit': 'gold',
    }

    nodes = list(cost_dict.keys())
    bar_width = 0.5

    # Initialize the bottom of the bars
    bottoms = np.zeros(len(nodes))

    fig, ax = plt.subplots()

    for attr in attributes_B:
        values = [cost_dict[node][attr] for node in cost_dict]
        ax.bar(nodes, values, bar_width, label=attr, color=colors[attr], bottom=bottoms)
        bottoms += values

        # Add text on bars
        for i, value in enumerate(values):
            if value > 0:
                ax.text(i, bottoms[i] - value / 2, f'{value:.1f}', ha='center', va='center', fontsize=8, color='white')

    # Add total values on top of bars
    total_values = [sum(cost_dict[node][attr] for attr in attributes_B) for node in cost_dict]
    for i, total in enumerate(total_values):
        ax.text(i, total + 2, f'{total:.1f}', ha='center', va='bottom', fontsize=10)

    ax.set_title('Supply Chain Cost Structure on Common Planning Unit')
    ax.set_xlabel('Node')
    ax.set_ylabel('Amount')
    ax.legend(title='Attribute')

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()



# *******************************************
# P_month_data.csv 2 weekly 2 allocation
# *******************************************
def convert_monthly_to_weekly_p(df: pd.DataFrame, lot_size: int):
    """
    Convert P_month_data.csv to weekly format with P_lot IDs.
    
    Parameters:
        df (pd.DataFrame): Monthly production data.
        lot_size (int): Lot size for production units.

    Returns:
        Tuple[pd.DataFrame, int, int]: Weekly production DataFrame with P_lots, planning range, and starting year.
    """

    # 1. 計画期間の取得
    start_year = df["year"].min()
    end_year = df["year"].max()
    plan_year_st = int(start_year)
    plan_range = int(end_year - start_year + 2)  # +1年分の余剰を含む

    # 2. データ整形（月次→日次）
    df = df.melt(id_vars=["product_name", "node_name", "year"], var_name="month", value_name="value")
    df["month"] = df["month"].str[1:].astype(int)
    df["year"] = df["year"].astype(int)

    df_daily = pd.DataFrame()
    for _, row in df.iterrows():
        year, month, value = row["year"], row["month"], row["value"]
        if pd.isna(value): continue
        days = pd.Timestamp(year, month, 1).days_in_month
        dates = pd.date_range(f"{year}-{month:02d}-01", periods=days)
        daily = pd.DataFrame({
            "product_name": row["product_name"],
            "node_name": row["node_name"],
            "date": dates,
            "value": [value] * days
        })
        df_daily = pd.concat([df_daily, daily])

    # 3. ISO週に変換
    df_daily["iso_year"] = df_daily["date"].dt.isocalendar().year
    df_daily["iso_week"] = df_daily["date"].dt.isocalendar().week.astype(str).str.zfill(2)

    df_weekly = df_daily.groupby(
        ["product_name", "node_name", "iso_year", "iso_week"]
    )["value"].sum().reset_index()

    # 4. P_lot数とlot ID生成
    df_weekly["P_lot"] = df_weekly["value"].apply(lambda x: math.ceil(x / lot_size))
    df_weekly["lot_id_list"] = df_weekly.apply(generate_p_lot_ids, axis=1)

    return df_weekly, plan_range, plan_year_st


def generate_p_lot_ids(row):
    lot_count = row["P_lot"]
    return [
        f"P_{row['node_name']}_{row['iso_year']}{row['iso_week']}_{i+1:04d}"
        for i in range(lot_count)
    ]




# ********************************:

def set_df_Plots2psi4supply(nodes_outbound: dict, df_weekly: pd.DataFrame, plan_year_st: int):
    """
    convert_monthly_to_weekly_p() で作成された P_lots を週別に psi4supply[w][3] にセットする。

    Parameters:
        nodes_outbound (dict): ノード名 → Nodeインスタンスの辞書（通常は self.nodes_outbound）
        df_weekly (DataFrame): 週次展開された P_lot データ（lot_id_list 列を含む）
        plan_year_st (int): 計画開始年（PSI Planner 全体で使用される基準年）
    """
    for _, row in df_weekly.iterrows():
        node_name = row["node_name"]
        iso_year = int(row["iso_year"])
        iso_week = int(row["iso_week"])
        lot_ids = row["lot_id_list"]

        # 年を跨ぐ週インデックス計算（PSI Plannerの週ベース表現に合わせる）
        week_index = (iso_year - plan_year_st) * 53 + int(iso_week)

        if node_name not in nodes_outbound:
            print(f"[Warning] Node '{node_name}' not found in nodes_outbound.")
            continue

        node = nodes_outbound[node_name]

        if len(node.psi4supply) <= week_index:
            print(f"[Warning] Week index {week_index} exceeds range for node '{node_name}'.")
            continue

        # psi4supply[w][3] = Production Lots
        node.psi4supply[week_index][3].extend(lot_ids)




from collections import defaultdict
from typing import Dict, List, Tuple

def perform_allocation(node, demand_map: Dict[int, List[str]], supply_weeks: List[Dict], lot_links_enabled=True) -> Tuple[Dict[int, List[str]], List[Dict], List[str]]:
    """
    指定ノードに対して需要S_lotsを供給週に割り当て、psi4supplyに流し込む。

    Parameters:
        node: Nodeインスタンス
        demand_map: {week: [S_lot_id, ...]} の辞書（psi4demandから抽出）
        supply_weeks: [{'week': w, 'capacity': n}, ...] 形式の供給スロット
        lot_links_enabled: 紐付け情報を保持するかどうか

    Returns:
        Tuple of:
            - allocation_result: {week: [S_lot_id, ...]}
            - allocation_links: [{'s_lot': ..., 'p_week': ...}]
            - warnings: [str, ...]
    """

    allocation_result = defaultdict(list)
    allocation_links = []
    warnings = []

    week_capacity = {w['week']: w['capacity'] for w in supply_weeks}
    sorted_weeks = sorted(week_capacity.keys())
    all_lots = []

    for w in sorted(demand_map):
        all_lots.extend(demand_map[w])

    week_idx = 0
    for s_lot in all_lots:
        attempts = 0
        assigned = False

        while attempts < len(sorted_weeks):
            current_week = sorted_weeks[week_idx % len(sorted_weeks)]

            if len(allocation_result[current_week]) < week_capacity[current_week]:
                allocation_result[current_week].append(s_lot)
                if lot_links_enabled:
                    allocation_links.append({
                        "s_lot": s_lot,
                        "p_week": current_week
                    })
                assigned = True
                break

            week_idx += 1
            attempts += 1

        if not assigned:
            warnings.append(f"Cannot allocate {s_lot}: all weeks full")

        week_idx += 1

    # PSI Planner node に反映
    for w, lots in allocation_result.items():
        node.psi4supply[w][3] = lots  # P(w)スロット

    if lot_links_enabled:
        node.allocation_links = allocation_links  # optional: 保存用

    return dict(allocation_result), allocation_links, warnings


# **** MyGPT messages ****
#### この関数を使うことで、load_data_files() や allocation phase の整理が簡単になり、GUI上でも拡張しやすくなります。

#### 必要であれば、allocation_links をCSV出力したり、可視化したりする関数も追加できます。ご希望があればお知らせください。
# *******************************************
# End of P_month_data.csv 2 weekly 2 allocation
# *******************************************









# gui/app.py
class PSIPlannerApp:
    def __init__(self, root, config):
    #def __init__(self, root):

        self.root = root
        self.config = config
        self.root.title(self.config.APP_NAME)
        
        self.tree_structure = None

        # 必ず setup_ui を先に呼び出す
        self.setup_ui()
        
        # 必要な初期化処理を後から呼び出す
        self.initialize_parameters()

        #@ STOP moved to config.py
        #self.lot_size     = 2000      # 初期値
        #self.plan_year_st = 2022      # 初期値
        #self.plan_range   = 2         # 初期値
        #self.pre_proc_LT  = 13        # 初期値 13week = 3month
        #self.market_potential = 0     # 初期値 0
        #self.target_share     = 0.5   # 初期値 0.5 = 50%
        #self.total_supply     = 0     # 初期値 0


        # ********************************
        # PSI planner
        # ********************************
        self.outbound_data = None
        self.inbound_data = None

        # PySI tree
        self.root_node_outbound = None
        self.nodes_outbound     = None
        self.leaf_nodes_out     = []

        self.root_node_inbound  = None
        self.nodes_inbound      = None
        self.leaf_nodes_in      = []

        self.root_node_out_opt  = None
        self.nodes_out_opt      = None
        self.leaf_nodes_opt     = []


        self.optimized_root     = None
        self.optimized_nodes    = None



        self.node_psi_dict_In4Dm = {}  # 需要側 PSI 辞書
        self.node_psi_dict_In4Sp = {}  # 供給側 PSI 辞書



        # Evaluation on PSI
        self.total_revenue = 0
        self.total_profit  = 0
        self.profit_ratio  = 0

        # view
        self.G = None

        # Optimise
        self.Gdm_structure = None

        self.Gdm = None
        self.Gsp = None

        self.pos_E2E = None

        self.flowDict_opt = {} #None
        self.flowCost_opt = {} #None

        self.total_supply_plan = 0

        # loading files
        self.directory = None
        self.load_directory = None

        self.base_leaf_name = None

        # supply_plan / decoupling / buffer stock
        self.decouple_node_dic = {}

        self.decouple_node_selected = []







    def setup_ui(self):

        print("setup_ui is processing")

        # フォントの設定
        custom_font = tkfont.Font(family="Helvetica", size=12)
        self.root.option_add('*TearOffMenu*Font', custom_font)
        self.root.option_add('*Menu*Font', custom_font)

        style = ttk.Style()
        style.configure("TLabel", font=('Helvetica', 10))
        style.configure("TButton", font=('Helvetica', 10))
        style.configure("Disabled.TButton", font=('Helvetica', 10))

        # メニューバーの作成
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="OPEN: select Directory", command=self.load_data_files)
        file_menu.add_separator()
        file_menu.add_command(label="SAVE: to Directory", command=self.save_to_directory)
        file_menu.add_command(label="LOAD: from Directory", command=self.load_from_directory)
        file_menu.add_separator()
        file_menu.add_command(label="EXIT", command=self.on_exit)
        menubar.add_cascade(label=" FILE  ", menu=file_menu)

        optimize_menu = tk.Menu(menubar, tearoff=0)
        optimize_menu.add_command(label="Save Objective Value", command=self.Save_Objective_Value)
        optimize_menu.add_separator()
        optimize_menu.add_command(label="Weight: Cost Stracture on Common Plan Unit", command=self.show_cost_stracture_bar_graph)
        optimize_menu.add_command(label="Capacity: Market Demand", command=self.show_month_data_csv)
        menubar.add_cascade(label="Optimize Parameter", menu=optimize_menu)

        report_menu = tk.Menu(menubar, tearoff=0)
        report_menu.add_command(label="Outbound: PSI to csv file", command=self.outbound_psi_to_csv)
        report_menu.add_command(label="Outbound: Lot by Lot data to csv", command=self.outbound_lot_by_lot_to_csv)
        report_menu.add_separator()
        report_menu.add_command(label="Inbound: PSI to csv file", command=self.inbound_psi_to_csv)
        report_menu.add_command(label="Inbound: Lot by Lot data to csv", command=self.inbound_lot_by_lot_to_csv)
        report_menu.add_separator()
        report_menu.add_command(label="Value Chain: Cost Stracture a Lot", command=self.lot_cost_structure_to_csv)
        report_menu.add_command(label="Supply Chain: Revenue Profit", command=self.supplychain_performance_to_csv)
        menubar.add_cascade(label="Report", menu=report_menu)

        revenue_profit_menu = tk.Menu(menubar, tearoff=0)
        revenue_profit_menu.add_command(label="Revenue and Profit", command=self.show_revenue_profit)
        menubar.add_cascade(label="Revenue and Profit", menu=revenue_profit_menu)

        cashflow_menu = tk.Menu(menubar, tearoff=0)
        cashflow_menu.add_command(label="PSI Price for CF", command=self.psi_price4cf)
        cashflow_menu.add_command(label="Cash Out&In&Net", command=self.cashflow_out_in_net)
        menubar.add_cascade(label="Cash Flow", menu=cashflow_menu)

        overview_menu = tk.Menu(menubar, tearoff=0)
        overview_menu.add_command(label="3D overview on Lots based Plan", command=self.show_3d_overview)
        menubar.add_cascade(label="3D overview", menu=overview_menu)

        self.root.config(menu=menubar)

        # 右側フレーム：パラメータ・評価表示・ボタン類
        self.frame = ttk.Frame(self.root)
        self.frame.pack(side=tk.RIGHT, fill=tk.Y)

        # --- 最上段：Global Parameters ---
        for label, attr, val in [
            ("MarketPotential", "gmp_entry", ""),
            ("TargetShare (%)", "ts_entry", self.config.DEFAULT_TARGET_SHARE * 100),
            ("Total Supply:    ", "tsp_entry", "")
        ]:
            ttk.Label(self.frame, text=label, background='navy', foreground='white', font=('Helvetica', 10, 'bold')).pack(padx=2, pady=2)
            entry = tk.Entry(self.frame, width=10)
            if val != "":
                entry.insert(0, val)
            entry.pack(padx=2, pady=2)
            if attr == "tsp_entry":
                entry.config(bg='lightgrey')
            setattr(self, attr, entry)

        self.gmp_entry.bind("<Return>", self.update_total_supply_plan)
        self.ts_entry.bind("<Return>", self.update_total_supply_plan)

        ttk.Label(self.frame, text="\n\n").pack()

        # --- 計画関連パラメータ ---
        for label, attr, val in [
            ("Lot Size:", "lot_size_entry", self.config.DEFAULT_LOT_SIZE),
            ("Plan Year Start:", "plan_year_entry", self.config.DEFAULT_START_YEAR),
            ("Plan Range:", "plan_range_entry", self.config.DEFAULT_PLAN_RANGE),
            ("pre_proc_LT:", "pre_proc_LT_entry", self.config.DEFAULT_PRE_PROC_LT)
        ]:
            ttk.Label(self.frame, text=label).pack()
            entry = tk.Entry(self.frame, width=10)
            entry.insert(0, str(val))
            entry.pack()
            setattr(self, attr, entry)

        ttk.Label(self.frame, text="\n\n").pack()

        # --- Demand ボタン群 ---
        self.Demand_Pl_button = ttk.Button(self.frame, text="Demand Planning", command=lambda: None, state="disabled", style="Disabled.TButton")
        self.Demand_Pl_button.pack()
        self.Demand_Lv_button = ttk.Button(self.frame, text="Demand Leveling", command=lambda: None, state="disabled", style="Disabled.TButton")
        self.Demand_Lv_button.pack()

        ttk.Label(self.frame, text="\n\n").pack()

        # --- Plan Engine ボタン群 ---
        for label, attr, cmd in [
            ("Supply Planning ", "supply_planning_button", self.supply_planning),
            ("Eval Buffer Stock ", "eval_buffer_stock_button", self.eval_buffer_stock),
            ("OPT Supply Alloc", "optimize_button", self.optimize_network),
            ("Inbound DmBw P", "Inbound_DmBw_button", self.Inbound_DmBw),
            ("Inbound SpFw P", "Inbound_SpFw_button", self.Inbound_SpFw)
        ]:
            button = ttk.Button(self.frame, text=label, command=cmd)
            button.pack()
            setattr(self, attr, button)

        ttk.Label(self.frame, text="\n\n").pack()

        # --- 最下段：評価結果表示 ---
        for label, attr in [
            ("Total Revenue:", "total_revenue_entry"),
            ("Total Profit:     ", "total_profit_entry"),
            ("Profit Ratio:     ", "profit_ratio_entry")
        ]:
            ttk.Label(self.frame, text=label, background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold')).pack(padx=2, pady=2)
            entry = tk.Entry(self.frame, width=10, state='readonly')
            entry.pack(padx=2, pady=2)
            setattr(self, attr, entry)

        # --- 左側中央エリア：グラフエリア（ネットワーク＋PSI） ---
        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.network_frame = ttk.Frame(self.plot_frame)
        self.network_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.fig_network, self.ax_network = plt.subplots(figsize=(4, 8))
        self.canvas_network = FigureCanvasTkAgg(self.fig_network, master=self.network_frame)
        self.canvas_network.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.fig_network.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        self.psi_frame = ttk.Frame(self.plot_frame)
        self.psi_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_psi = tk.Canvas(self.psi_frame)
        self.scrollbar = ttk.Scrollbar(self.psi_frame, orient="vertical", command=self.canvas_psi.yview)
        self.scrollable_frame = ttk.Frame(self.canvas_psi)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas_psi.configure(scrollregion=self.canvas_psi.bbox("all")))

        self.scroll_window = self.canvas_psi.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def update_scroll_width():
            self.canvas_psi.update_idletasks()
            bbox = self.canvas_psi.bbox(self.scroll_window)
            if bbox:
                width = bbox[2] - bbox[0] + 20  # 余白調整
                self.canvas_psi.itemconfig(self.scroll_window, width=width)

        #@250703 STOP
        #self.scrollable_frame.bind("<Configure>", lambda e: [
        #    self.canvas_psi.configure(scrollregion=self.canvas_psi.bbox("all")),
        #    update_scroll_width()
        #])


        self.canvas_psi.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_psi.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")



    def setup_ui_OLD2507031540(self):

        print("setup_ui is processing")

        # フォントの設定
        custom_font = tkfont.Font(family="Helvetica", size=12)

        # メニュー全体のフォントサイズを設定
        self.root.option_add('*TearOffMenu*Font', custom_font)
        self.root.option_add('*Menu*Font', custom_font)

        # フォントスタイルの統一設定
        style = ttk.Style()
        style.configure("TLabel", font=('Helvetica', 10))
        style.configure("TButton", font=('Helvetica', 10))
        style.configure("Disabled.TButton", font=('Helvetica', 10))

        # メニューバーの作成
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="OPEN: select Directory", command=self.load_data_files)
        file_menu.add_separator()
        file_menu.add_command(label="SAVE: to Directory", command=self.save_to_directory)
        file_menu.add_command(label="LOAD: from Directory", command=self.load_from_directory)
        file_menu.add_separator()
        file_menu.add_command(label="EXIT", command=self.on_exit)
        menubar.add_cascade(label=" FILE  ", menu=file_menu)

        optimize_menu = tk.Menu(menubar, tearoff=0)
        optimize_menu.add_command(label="Save Objective Value", command=self.Save_Objective_Value)
        optimize_menu.add_separator()
        optimize_menu.add_command(label="Weight: Cost Stracture on Common Plan Unit", command=self.show_cost_stracture_bar_graph)
        optimize_menu.add_command(label="Capacity: Market Demand", command=self.show_month_data_csv)
        menubar.add_cascade(label="Optimize Parameter", menu=optimize_menu)

        report_menu = tk.Menu(menubar, tearoff=0)
        report_menu.add_command(label="Outbound: PSI to csv file", command=self.outbound_psi_to_csv)
        report_menu.add_command(label="Outbound: Lot by Lot data to csv", command=self.outbound_lot_by_lot_to_csv)
        report_menu.add_separator()
        report_menu.add_command(label="Inbound: PSI to csv file", command=self.inbound_psi_to_csv)
        report_menu.add_command(label="Inbound: Lot by Lot data to csv", command=self.inbound_lot_by_lot_to_csv)
        report_menu.add_separator()
        report_menu.add_command(label="Value Chain: Cost Stracture a Lot", command=self.lot_cost_structure_to_csv)
        report_menu.add_command(label="Supply Chain: Revenue Profit", command=self.supplychain_performance_to_csv)
        menubar.add_cascade(label="Report", menu=report_menu)

        revenue_profit_menu = tk.Menu(menubar, tearoff=0)
        revenue_profit_menu.add_command(label="Revenue and Profit", command=self.show_revenue_profit)
        menubar.add_cascade(label="Revenue and Profit", menu=revenue_profit_menu)

        cashflow_menu = tk.Menu(menubar, tearoff=0)
        cashflow_menu.add_command(label="PSI Price for CF", command=self.psi_price4cf)
        cashflow_menu.add_command(label="Cash Out&In&Net", command=self.cashflow_out_in_net)
        menubar.add_cascade(label="Cash Flow", menu=cashflow_menu)

        overview_menu = tk.Menu(menubar, tearoff=0)
        overview_menu.add_command(label="3D overview on Lots based Plan", command=self.show_3d_overview)
        menubar.add_cascade(label="3D overview", menu=overview_menu)

        self.root.config(menu=menubar)

        # plot_frame の定義
        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Network Graph frameとax_networkの定義
        self.network_frame = ttk.Frame(self.plot_frame)
        self.network_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.fig_network, self.ax_network = plt.subplots(figsize=(4, 8))
        self.canvas_network = FigureCanvasTkAgg(self.fig_network, master=self.network_frame)
        self.canvas_network.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.fig_network.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        # PSIグラフエリアの定義（スクロール付き）
        self.psi_frame = ttk.Frame(self.plot_frame)
        self.psi_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas_psi = tk.Canvas(self.psi_frame)
        self.scrollbar = ttk.Scrollbar(self.psi_frame, orient="vertical", command=self.canvas_psi.yview)
        self.scrollable_frame = ttk.Frame(self.canvas_psi)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_psi.configure(scrollregion=self.canvas_psi.bbox("all"))
        )
        self.canvas_psi.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas_psi.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_psi.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # フレームの作成
        self.frame = ttk.Frame(self.root)
        self.frame.pack(side=tk.LEFT, fill=tk.Y)

        self.lot_size_label = ttk.Label(self.frame, text="Lot Size:")
        self.lot_size_label.pack(side=tk.TOP)
        self.lot_size_entry = tk.Entry(self.frame, width=10, font=('Helvetica', 10))
        self.lot_size_entry.pack(side=tk.TOP)
        self.lot_size_entry.insert(0, str(self.config.DEFAULT_LOT_SIZE))

        self.plan_year_label = ttk.Label(self.frame, text="Plan Year Start:")
        self.plan_year_label.pack(side=tk.TOP)
        self.plan_year_entry = tk.Entry(self.frame, width=10, font=('Helvetica', 10))
        self.plan_year_entry.pack(side=tk.TOP)
        self.plan_year_entry.insert(0, str(self.config.DEFAULT_START_YEAR))

        self.plan_range_label = ttk.Label(self.frame, text="Plan Range:")
        self.plan_range_label.pack(side=tk.TOP)
        self.plan_range_entry = tk.Entry(self.frame, width=10, font=('Helvetica', 10))
        self.plan_range_entry.pack(side=tk.TOP)
        self.plan_range_entry.insert(0, str(self.config.DEFAULT_PLAN_RANGE))

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.Demand_Pl_button = ttk.Button(
            self.frame,
            text="Demand Planning",
            command=lambda: None,
            state="disabled",
            style="Disabled.TButton"
        )
        self.Demand_Pl_button.pack(side=tk.TOP)

        self.pre_proc_LT_label = ttk.Label(self.frame, text="pre_proc_LT:")
        self.pre_proc_LT_label.pack(side=tk.TOP)
        self.pre_proc_LT_entry = tk.Entry(self.frame, width=10, font=('Helvetica', 10))
        self.pre_proc_LT_entry.pack(side=tk.TOP)
        self.pre_proc_LT_entry.insert(0, str(self.config.DEFAULT_PRE_PROC_LT))

        self.Demand_Lv_button = ttk.Button(
            self.frame,
            text="Demand Leveling",
            command=lambda: None,
            state="disabled",
            style="Disabled.TButton"
        )
        self.Demand_Lv_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.supply_planning_button = ttk.Button(self.frame, text="Supply Planning ", command=self.supply_planning)
        self.supply_planning_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.eval_buffer_stock_button = ttk.Button(self.frame, text="Eval Buffer Stock ", command=self.eval_buffer_stock)
        self.eval_buffer_stock_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.optimize_button = ttk.Button(self.frame, text="OPT Supply Alloc", command=self.optimize_network)
        self.optimize_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.Inbound_DmBw_button = ttk.Button(self.frame, text="Inbound DmBw P", command=self.Inbound_DmBw)
        self.Inbound_DmBw_button.pack(side=tk.TOP)

        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        self.Inbound_SpFw_button = ttk.Button(self.frame, text="Inbound SpFw P", command=self.Inbound_SpFw)
        self.Inbound_SpFw_button.pack(side=tk.TOP)

        # Evaluation result area
        self.eval_frame = ttk.Frame(self.plot_frame)
        self.eval_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.total_revenue_label = ttk.Label(self.eval_frame, text="Total Revenue:", font=('Helvetica', 10))
        self.total_revenue_label.pack(side=tk.LEFT, padx=5)
        self.total_revenue_entry = tk.Entry(self.eval_frame, width=10, font=('Helvetica', 10), state='readonly')
        self.total_revenue_entry.pack(side=tk.LEFT, padx=5)

        self.total_profit_label = ttk.Label(self.eval_frame, text="Total Profit:", font=('Helvetica', 10))
        self.total_profit_label.pack(side=tk.LEFT, padx=5)
        self.total_profit_entry = tk.Entry(self.eval_frame, width=10, font=('Helvetica', 10), state='readonly')
        self.total_profit_entry.pack(side=tk.LEFT, padx=5)

        self.profit_ratio_label = ttk.Label(self.eval_frame, text="Profit Ratio:", font=('Helvetica', 10))
        self.profit_ratio_label.pack(side=tk.LEFT, padx=5)
        self.profit_ratio_entry = tk.Entry(self.eval_frame, width=10, font=('Helvetica', 10), state='readonly')
        self.profit_ratio_entry.pack(side=tk.LEFT, padx=5)

        # Global Parameters input fields (gmp, ts, tsp)
        self.param_frame = ttk.Frame(self.plot_frame)
        self.param_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.gmp_label = ttk.Label(self.param_frame, text="Market Potential:", font=('Helvetica', 10))
        self.gmp_label.pack(side=tk.LEFT, padx=5)
        self.gmp_entry = tk.Entry(self.param_frame, width=10, font=('Helvetica', 10))
        self.gmp_entry.pack(side=tk.LEFT, padx=5)

        self.ts_label = ttk.Label(self.param_frame, text="TargetShare(%)", font=('Helvetica', 10))
        self.ts_label.pack(side=tk.LEFT, padx=5)
        self.ts_entry = tk.Entry(self.param_frame, width=5, font=('Helvetica', 10))
        self.ts_entry.pack(side=tk.LEFT, padx=5)

        self.ts_entry.insert(0, self.config.DEFAULT_TARGET_SHARE * 100)

        self.tsp_label = ttk.Label(self.param_frame, text="Total Supply:", font=('Helvetica', 10))
        self.tsp_label.pack(side=tk.LEFT, padx=5)
        self.tsp_entry = tk.Entry(self.param_frame, width=10, font=('Helvetica', 10))
        self.tsp_entry.pack(side=tk.LEFT, padx=5)
        self.tsp_entry.config(bg='lightgrey')

        self.gmp_entry.bind("<Return>", self.update_total_supply_plan)
        self.ts_entry.bind("<Return>", self.update_total_supply_plan)





    def setup_ui_OLD250703(self):

        print("setup_ui is processing")

        #@250703 STOP
        ## フォントの設定
        #custom_font = tkfont.Font(family="Helvetica", size=12)

        ## メニュー全体のフォントサイズを設定
        #self.root.option_add('*TearOffMenu*Font', custom_font)
        #self.root.option_add('*Menu*Font', custom_font)




        # フォントの設定
        custom_font = tkfont.Font(family="Helvetica", size=12)

        # メニュー全体のフォントサイズを設定
        self.root.option_add('*TearOffMenu*Font', custom_font)
        self.root.option_add('*Menu*Font', custom_font)

        # フォントスタイルの統一設定
        style = ttk.Style()
        style.configure("TLabel", font=('Helvetica', 10))
        style.configure("TButton", font=('Helvetica', 10))
        style.configure("Disabled.TButton", font=('Helvetica', 10))





        # メニューバーの作成
        menubar = tk.Menu(self.root)

        # スタイルの設定
        style = ttk.Style()
        style.configure("TMenubutton", font=("Helvetica", 12))

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="OPEN: select Directory", command=self.load_data_files)
        file_menu.add_separator()
        file_menu.add_command(label="SAVE: to Directory", command=self.save_to_directory)

        file_menu.add_command(label="LOAD: from Directory", command=self.load_from_directory)

        file_menu.add_separator()
        file_menu.add_command(label="EXIT", command=self.on_exit)

        menubar.add_cascade(label=" FILE  ", menu=file_menu)


        # Optimize Parameter menu
        optimize_menu = tk.Menu(menubar, tearoff=0)
        optimize_menu.add_command(label="Save Objective Value", command=self.Save_Objective_Value)

        optimize_menu.add_separator()

        optimize_menu.add_command(label="Weight: Cost Stracture on Common Plan Unit", command=self.show_cost_stracture_bar_graph)
        optimize_menu.add_command(label="Capacity: Market Demand", command=self.show_month_data_csv)

        menubar.add_cascade(label="Optimize Parameter", menu=optimize_menu)



        # Report menu
        report_menu = tk.Menu(menubar, tearoff=0)

        report_menu.add_command(label="Outbound: PSI to csv file", command=self.outbound_psi_to_csv)

        report_menu.add_command(label="Outbound: Lot by Lot data to csv", command=self.outbound_lot_by_lot_to_csv)

        report_menu.add_separator()

        report_menu.add_command(label="Inbound: PSI to csv file", command=self.inbound_psi_to_csv)
        report_menu.add_command(label="Inbound: Lot by Lot data to csv", command=self.inbound_lot_by_lot_to_csv)

        report_menu.add_separator()

        report_menu.add_separator()

        report_menu.add_command(label="Value Chain: Cost Stracture a Lot", command=self.lot_cost_structure_to_csv)

        report_menu.add_command(label="Supply Chain: Revenue Profit", command=self.supplychain_performance_to_csv)



        #report_menu.add_separator()
        #
        #report_menu.add_command(label="PSI for Excel", command=self.psi_for_excel)

        menubar.add_cascade(label="Report", menu=report_menu)



        # Revenue and Profit menu
        revenue_profit_menu = tk.Menu(menubar, tearoff=0)
        revenue_profit_menu.add_command(label="Revenue and Profit", command=self.show_revenue_profit)
        menubar.add_cascade(label="Revenue and Profit", menu=revenue_profit_menu)


        # Cash Flow analysis menu
        cashflow_menu = tk.Menu(menubar, tearoff=0)
        cashflow_menu.add_command(label="PSI Price for CF", command=self.psi_price4cf)
        cashflow_menu.add_command(label="Cash Out&In&Net", command=self.cashflow_out_in_net)

        menubar.add_cascade(label="Cash Flow", menu=cashflow_menu)


        # 3D overview menu
        overview_menu = tk.Menu(menubar, tearoff=0)
        overview_menu.add_command(label="3D overview on Lots based Plan", command=self.show_3d_overview)
        menubar.add_cascade(label="3D overview", menu=overview_menu)

        self.root.config(menu=menubar)


        #@250701 ADD
        # <<< ここに plot_frame の定義を追加 >>>
        self.plot_frame = ttk.Frame(self.root)
        self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)





        # カレンダー設定とフィルタ処理（週番号ではなく yymm に基づいて正確に制限）
        cal = Calendar445(
            start_year=self.plan_year_st,
            plan_range=self.plan_range,
            use_13_months=True,
            holiday_country="JP"
        )
        week_start = 1
        week_end = self.plan_range * 53
        max_year = self.plan_year_st + self.plan_range - 1
        week_to_yymm_all = cal.get_week_labels()
        week_to_yymm = {w: y for w, y in week_to_yymm_all.items() if int(str(y)[:2]) <= max_year % 100}
        month_end_weeks = [w for w in cal.get_month_end_weeks() if w in week_to_yymm]
        holiday_weeks = [w for w in cal.get_holiday_weeks() if w in week_to_yymm]







        # フレームの作成
        self.frame = ttk.Frame(self.root)
        self.frame.pack(side=tk.LEFT, fill=tk.Y)

        # Lot size entry
        self.lot_size_label = ttk.Label(self.frame, text="Lot Size:")
        self.lot_size_label.pack(side=tk.TOP)
        self.lot_size_entry = ttk.Entry(self.frame, width=10)
        self.lot_size_entry.pack(side=tk.TOP)

        #@250117 UPDATE
        self.lot_size_entry.insert(0, str(self.config.DEFAULT_LOT_SIZE))  # 初期値を設定
        #self.lot_size_entry.insert(0, str(self.lot_size))  # 初期値を設定

        # Plan Year Start entry
        self.plan_year_label = ttk.Label(self.frame, text="Plan Year Start:")
        self.plan_year_label.pack(side=tk.TOP)
        self.plan_year_entry = ttk.Entry(self.frame, width=10)
        self.plan_year_entry.pack(side=tk.TOP)


        self.plan_year_entry.insert(0, str(self.config.DEFAULT_START_YEAR))  # 初期値を設定
        #self.plan_year_entry.insert(0, str(self.plan_year_st))  # 初期値を設定

        # Plan Range entry
        self.plan_range_label = ttk.Label(self.frame, text="Plan Range:")
        self.plan_range_label.pack(side=tk.TOP)
        self.plan_range_entry = ttk.Entry(self.frame, width=10)
        self.plan_range_entry.pack(side=tk.TOP)


        self.plan_range_entry.insert(0, str(self.config.DEFAULT_PLAN_RANGE))  # 初期値を設定
        #self.plan_range_entry.insert(0, str(self.plan_range))  # 初期値を設定

        # 1行分の空白を追加
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)



        #@250120 RUN
        # Demand Planning ボタン（グレイアウト）
        self.Demand_Pl_button = ttk.Button(
            self.frame,
            text="Demand Planning",
            command=lambda: None,  # 無効化
            state="disabled",  # ボタンを無効化
            style="Disabled.TButton"  # スタイルを適用
        )
        self.Demand_Pl_button.pack(side=tk.TOP)


        #@250120 STOP
        ## Demand Planning buttons
        #self.Demand_Pl_button = ttk.Button(self.frame, text="Demand Planning", command=self.demand_planning)
        #self.Demand_Pl_button.pack(side=tk.TOP)




        # Plan Year Start entry
        self.pre_proc_LT_label = ttk.Label(self.frame, text="pre_proc_LT:")
        self.pre_proc_LT_label.pack(side=tk.TOP)
        self.pre_proc_LT_entry = ttk.Entry(self.frame, width=10)
        self.pre_proc_LT_entry.pack(side=tk.TOP)


        self.pre_proc_LT_entry.insert(0, str(self.config.DEFAULT_PRE_PROC_LT))  # 初期値を設定
        #self.pre_proc_LT_entry.insert(0, str(self.pre_proc_LT))  # 初期値を設定


        #@250120 RUN
        # Demand Leveling ボタン（グレイアウト）
        self.Demand_Lv_button = ttk.Button(
            self.frame,
            text="Demand Leveling",
            command=lambda: None,  # 無効化
            state="disabled",  # ボタンを無効化
            style="Disabled.TButton"  # スタイルを適用
        )
        self.Demand_Lv_button.pack(side=tk.TOP)


        #@250120 STOP
        ## Demand Leveling button
        #self.Demand_Lv_button = ttk.Button(self.frame, text="Demand Leveling", command=self.demand_leveling)
        #self.Demand_Lv_button.pack(side=tk.TOP)





        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Supply Planning button
        self.supply_planning_button = ttk.Button(self.frame, text="Supply Planning ", command=self.supply_planning)
        self.supply_planning_button.pack(side=tk.TOP)

        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Eval_buffer_stock buttons
        self.eval_buffer_stock_button = ttk.Button(self.frame, text="Eval Buffer Stock ", command=self.eval_buffer_stock)
        self.eval_buffer_stock_button.pack(side=tk.TOP)

        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Optimize Network button
        self.optimize_button = ttk.Button(self.frame, text="OPT Supply Alloc", command=self.optimize_network)
        self.optimize_button.pack(side=tk.TOP)



        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Optimize Network button
        self.Inbound_DmBw_button = ttk.Button(self.frame, text="Inbound DmBw P", command=self.Inbound_DmBw)
        self.Inbound_DmBw_button.pack(side=tk.TOP)



        # add a blank line
        self.space_label = ttk.Label(self.frame, text="")
        self.space_label.pack(side=tk.TOP)

        # Optimize Network button
        self.Inbound_SpFw_button = ttk.Button(self.frame, text="Inbound SpFw P", command=self.Inbound_SpFw)
        self.Inbound_SpFw_button.pack(side=tk.TOP)








        # Network Graph frame
        self.network_frame = ttk.Frame(self.plot_frame)
        self.network_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # expand 追加、fill=BOTH

        #@250701 STOP
        ## Plot area divided into two frames
        #self.plot_frame = ttk.Frame(self.root)
        #self.plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        #@250701 STOP
        # Network Graph frame
        #self.network_frame = ttk.Frame(self.plot_frame)
        #self.network_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ## Network Graph frame
        #self.network_frame = ttk.Frame(self.plot_frame, width=500)  # 横幅指定を追加
        #self.network_frame.pack(side=tk.LEFT, fill=tk.Y)  # fill=tk.Y に変更して固定幅化


        # New Frame for Parameters at the top of the network_frame
        self.param_frame = ttk.Frame(self.network_frame)
        self.param_frame.pack(side=tk.TOP, fill=tk.X)


        # Global Market Potential, Target Share, Total Supply Plan input fields arranged horizontally
        self.gmp_label = tk.Label(self.param_frame, text="Market Potential:", background='navy', foreground='white', font=('Helvetica', 10, 'bold'))
        self.gmp_label.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)
        self.gmp_entry = tk.Entry(self.param_frame, width=10)
        self.gmp_entry.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)

        self.ts_label = tk.Label(self.param_frame, text="TargetShare (%)", background='navy', foreground='white', font=('Helvetica', 10, 'bold'))
        self.ts_label.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)
        self.ts_entry = tk.Entry(self.param_frame, width=5)
        self.ts_entry.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)



        self.ts_entry.insert(0, self.config.DEFAULT_TARGET_SHARE * 100) # 初期値
        #self.ts_entry.insert(0, self.target_share * 100) # 初期値

        self.tsp_label = tk.Label(self.param_frame, text="Total Supply  :", background='navy', foreground='white', font=('Helvetica', 10, 'bold'))
        self.tsp_label.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)
        self.tsp_entry = tk.Entry(self.param_frame, width=10)
        self.tsp_entry.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=10)
        self.tsp_entry.config(bg='lightgrey')  # 背景色をlightgreyに設定




        # イベントバインディング
        self.gmp_entry.bind("<Return>", self.update_total_supply_plan)
        self.ts_entry.bind("<Return>", self.update_total_supply_plan)

        self.fig_network, self.ax_network = plt.subplots(figsize=(4, 8))  # 横幅を縮小
        self.canvas_network = FigureCanvasTkAgg(self.fig_network, master=self.network_frame)

        ##@250228 ADD STOP
        #self.canvas_network.get_tk_widget().config(width=500, height=300)  # 画面サイズを制限
        #self.canvas_network.get_tk_widget().pack(fill=tk.BOTH, expand=False)  # ウィンドウのリサイズを防ぐ

        #@250228 STOP RUN
        self.canvas_network.get_tk_widget().pack(fill=tk.BOTH, expand=True)




        self.fig_network.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)

        # Evaluation result area
        self.eval_frame = ttk.Frame(self.plot_frame)
        self.eval_frame.pack(side=tk.TOP, fill=tk.X, padx=(20, 0))  # 横方向に配置

        # Total Revenue
        self.total_revenue_label = ttk.Label(self.eval_frame, text="Total Revenue:", background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold'))
        self.total_revenue_label.pack(side=tk.LEFT, padx=5, pady=10)
        self.total_revenue_entry = ttk.Entry(self.eval_frame, width=10, state='readonly')
        self.total_revenue_entry.pack(side=tk.LEFT, padx=5, pady=10)

        # Total Profit
        self.total_profit_label = ttk.Label(self.eval_frame, text="Total Profit  :", background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold'))
        self.total_profit_label.pack(side=tk.LEFT, padx=5, pady=10)
        self.total_profit_entry = ttk.Entry(self.eval_frame, width=10, state='readonly')
        self.total_profit_entry.pack(side=tk.LEFT, padx=5, pady=10)




        # Profit Ratio
        self.profit_ratio_label = ttk.Label(self.eval_frame, text="Profit Ratio  :", background='darkgreen', foreground='white', font=('Helvetica', 10, 'bold'))
        self.profit_ratio_label.pack(side=tk.LEFT, padx=5, pady=10)
        self.profit_ratio_entry = ttk.Entry(self.eval_frame, width=10, state='readonly')
        self.profit_ratio_entry.pack(side=tk.LEFT, padx=5, pady=10)


        # PSI Graph scroll frame
        self.psi_frame = ttk.Frame(self.plot_frame)
        self.psi_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # これもそのままでOK

        #@250701 STOP
        ## PSI Graph scroll frame
        #self.psi_frame = ttk.Frame(self.plot_frame)
        #self.psi_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # side=tk.LEFT に変更

        #@250701 STOP
        # PSI Graph scroll frame (moved to below evaluation area)
        #self.psi_frame = ttk.Frame(self.plot_frame)
        #self.psi_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)



        self.canvas_psi = tk.Canvas(self.psi_frame)
        self.scrollbar = ttk.Scrollbar(self.psi_frame, orient="vertical", command=self.canvas_psi.yview)
        self.scrollable_frame = ttk.Frame(self.canvas_psi)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_psi.configure(
                scrollregion=self.canvas_psi.bbox("all")
            )
        )

        self.canvas_psi.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas_psi.configure(yscrollcommand=self.scrollbar.set)

        self.canvas_psi.pack(side="left", fill="both", expand=True)

        #@250702 UPDATE
        #self.scrollbar.pack(side="right", fill="y")
        self.scrollbar.pack(side="right", fill="y", expand=True)

        #@250120 STOP
        ## 初期化関数を呼び出してパラメータ設定
        #self.initialize_parameters()




    def update_total_supply_plan(self, event):
        try:
            market_potential = float(self.gmp_entry.get().replace(',', ''))
            target_share = float(self.ts_entry.get().replace('%', ''))/100
        except ValueError:
            print("Invalid input for Global Market Potential or Target Share.")
            return

        # Total Supply Planの再計算
        total_supply_plan = round(market_potential * target_share)

        self.total_supply_plan = total_supply_plan

        # Total Supply Planフィールドの更新
        self.tsp_entry.config(state='normal')
        self.tsp_entry.delete(0, tk.END)
        self.tsp_entry.insert(0, "{:,}".format(total_supply_plan))  # 3桁毎にカンマ区切りで表示
        self.tsp_entry.config(state='normal')



    def initialize_parameters(self):

        print("Initializing parameters")
        self.lot_size     = self.config.DEFAULT_LOT_SIZE
        self.plan_year_st = self.config.DEFAULT_START_YEAR
        self.plan_range   = self.config.DEFAULT_PLAN_RANGE

        self.pre_proc_LT  = self.config.DEFAULT_PRE_PROC_LT
    
        # self.market_potential = 0 # initial setting from "demand_generate"
        self.target_share = self.config.DEFAULT_TARGET_SHARE
        self.total_supply = 0










        if not hasattr(self, 'gmp_entry') or not hasattr(self, 'ts_entry') or not hasattr(self, 'tsp_entry'):
            raise AttributeError("Required UI components (gmp_entry, ts_entry, tsp_entry) have not been initialized.")


        print("Setting market potential and share")
        # Calculation and setting of Global Market Potential
        market_potential = getattr(self, 'market_potential', self.config.DEFAULT_MARKET_POTENTIAL)  # Including initial settings

        self.gmp_entry.delete(0, tk.END)
        self.gmp_entry.insert(0, "{:,}".format(market_potential))  # Display with comma separated thousands

        # Initial setting of Target Share (already set in setup_ui)

        # Calculation and setting of Total Supply Plan
        target_share = float(self.ts_entry.get().replace('%', ''))/100  # Convert string to float and remove %

        total_supply_plan = round(market_potential * target_share)
        self.tsp_entry.delete(0, tk.END)
        self.tsp_entry.insert(0, "{:,}".format(total_supply_plan))  # Display with comma separated thousands

        #self.global_market_potential  = global_market_potential

        self.market_potential         = market_potential
        self.target_share             = target_share           
        self.total_supply_plan        = total_supply_plan
        print(f"At initialization - market_potential: {self.market_potential}, target_share: {self.target_share}")  # Add log





    def updated_parameters(self):
        print(f"updated_parameters更新前 - market_potential: {self.market_potential}, target_share: {self.target_share}")  # ログ追加

        # Market Potentialの計算と設定
        market_potential = self.market_potential
        print("market_potential", market_potential)
        
        self.gmp_entry.delete(0, tk.END)
        self.gmp_entry.insert(0, "{:,}".format(market_potential))  # 3桁毎にカンマ区切りで表示

        # Target Shareの初期値設定（すでにsetup_uiで設定済み）
        #@ ADD: Keep the current target_share value if user has not entered a new value
        if self.ts_entry.get():
            target_share = float(self.ts_entry.get().replace('%', '')) / 100  # 文字列を浮動小数点数に変換して%を除去
        else:
            target_share = self.target_share

        # Total Supply Planの計算と設定
        total_supply_plan = round(market_potential * target_share)
        self.tsp_entry.delete(0, tk.END)
        self.tsp_entry.insert(0, "{:,}".format(total_supply_plan))  # 3桁毎にカンマ区切りで表示

        self.market_potential = market_potential
        self.target_share = target_share
        self.total_supply_plan = total_supply_plan

        print(f"updated_parameters更新時 - market_potential: {self.market_potential}, target_share: {self.target_share}")  # ログ追加





# ******************************
# actions
# ******************************

    def derive_weekly_capacity_from_plots(self):
        """
        node.psi4supply[w][3] に入っている P_lots の数をその週のキャパシティとみなして weekly_cap_dict を作成。
        """
        self.weekly_cap_dict = {}
    
        for node_name, node in self.nodes_outbound.items():
            self.weekly_cap_dict[node_name] = []
    
            for week_index, week_data in enumerate(node.psi4supply):
                lot_ids = week_data[3]
                if lot_ids:
                    self.weekly_cap_dict[node_name].append({
                        "week": week_index,
                        "capacity": len(lot_ids)
                    })

        print(f"[INFO] Weekly capacity derived from psi4supply for {len(self.weekly_cap_dict)} nodes")



#@250630 STOP GO
    def load_data_files(self):
        directory = filedialog.askdirectory(title="Select Data Directory")

        if directory:
            try:
                self.lot_size = int(self.lot_size_entry.get())
                self.plan_year_st = int(self.plan_year_entry.get())
                self.plan_range = int(self.plan_range_entry.get())
            except ValueError:
                print("Invalid input for lot size, plan year start, or plan range. Using default values.")

            self.outbound_data = []
            self.inbound_data = []

            data_file_list = os.listdir(directory)

            print("data_file_list", data_file_list)

            self.directory = directory
            self.load_directory = directory

            # --- Load Tree Structures ---
            if "profile_tree_outbound.csv" in data_file_list:
                file_path = os.path.join(directory, "profile_tree_outbound.csv")
                nodes_outbound, root_node_name_out = create_tree_set_attribute(file_path)
                root_node_outbound = nodes_outbound[root_node_name_out]

                def make_leaf_nodes(node, leaf_list):
                    if not node.children:
                        leaf_list.append(node.name)
                    for child in node.children:
                        make_leaf_nodes(child, leaf_list)
                    return leaf_list

                leaf_nodes_out = make_leaf_nodes(root_node_outbound, [])
                self.nodes_outbound = nodes_outbound
                self.root_node_outbound = root_node_outbound
                self.leaf_nodes_out = leaf_nodes_out
                set_positions(root_node_outbound)
                set_parent_all(root_node_outbound)
                print_parent_all(root_node_outbound)
            else:
                print("error: profile_tree_outbound.csv is missed")

            if "profile_tree_inbound.csv" in data_file_list:
                file_path = os.path.join(directory, "profile_tree_inbound.csv")
                nodes_inbound, root_node_name_in = create_tree_set_attribute(file_path)
                root_node_inbound = nodes_inbound[root_node_name_in]
                self.nodes_inbound = nodes_inbound
                self.root_node_inbound = root_node_inbound
                set_positions(root_node_inbound)
                set_parent_all(root_node_inbound)
                print_parent_all(root_node_inbound)
            else:
                print("error: profile_tree_inbound.csv is missed")

            if "node_cost_table_outbound.csv" in data_file_list:
                read_set_cost(os.path.join(directory, "node_cost_table_outbound.csv"), self.nodes_outbound)
            else:
                print("error: node_cost_table_outbound.csv is missed")

            if "node_cost_table_inbound.csv" in data_file_list:
                read_set_cost(os.path.join(directory, "node_cost_table_inbound.csv"), self.nodes_inbound)
            else:
                print("error: node_cost_table_inbound.csv is missed")

            if "S_month_data.csv" in data_file_list:
                in_file_path = os.path.join(directory, "S_month_data.csv")
                df_weekly, plan_range, plan_year_st = process_monthly_demand(in_file_path, self.lot_size)
                self.plan_year_st = plan_year_st
                self.plan_range = plan_range
                self.plan_year_entry.delete(0, tk.END)
                self.plan_year_entry.insert(0, str(self.plan_year_st))
                self.plan_range_entry.delete(0, tk.END)
                self.plan_range_entry.insert(0, str(self.plan_range))
                df_weekly.to_csv(os.path.join(directory, "S_iso_week_data.csv"), index=False)
            else:
                print("error: S_month_data.csv is missed")

            root_node_outbound.set_plan_range_lot_counts(plan_range, plan_year_st)
            root_node_inbound.set_plan_range_lot_counts(plan_range, plan_year_st)

            node_psi_dict_Ot4Dm = make_psi_space_dict(root_node_outbound, {}, plan_range)
            node_psi_dict_Ot4Sp = make_psi_space_dict(root_node_outbound, {}, plan_range)
            self.node_psi_dict_In4Dm = make_psi_space_dict(root_node_inbound, {}, plan_range)
            self.node_psi_dict_In4Sp = make_psi_space_dict(root_node_inbound, {}, plan_range)
            set_dict2tree_psi(root_node_outbound, "psi4demand", node_psi_dict_Ot4Dm)
            set_dict2tree_psi(root_node_outbound, "psi4supply", node_psi_dict_Ot4Sp)
            set_dict2tree_psi(root_node_inbound, "psi4demand", self.node_psi_dict_In4Dm)
            set_dict2tree_psi(root_node_inbound, "psi4supply", self.node_psi_dict_In4Sp)


            # **********************************
            # make&set weekly demand "Slots" on leaf_node, propagate2root
            # initial setting psi4"demand"[w][0] to psi4"supply"[w][0]
            # **********************************
            #set_df_Slots2psi4demand(self.root_node_outbound, df_weekly)
            set_df_Slots2psi4demand(root_node_outbound, df_weekly)


            # convert_monthly_to_weekly() → set_df_Slots2psi4demand() の後
            for node in self.nodes_outbound.values():
                print(f"[{node.name}] demand lots per week:",
                      [len(node.psi4demand[w][0]) for w in range(1, self.plan_range + 1)])

                      #[len(node.psi4demand[w][0]) for w in range(1, min(self.plan_range + 1, 10))])






            # ****************************************************
            # --- Allocation Logic from P_month_data.csv ---
            # ****************************************************



# ****************************************************
#@250708 インデントを修正する
# ****************************************************



#250708Tryexcept_indent.py


if "P_month_data.csv" in data_file_list:
    try:
        p_path = os.path.join(self.directory, "P_month_data.csv")
        df_p_month = pd.read_csv(p_path, encoding='utf-8-sig')

        unique_nodes = df_p_month["node_name"].unique()

        # 月次→週次変換＆Lot ID生成（複数年対応）
        df_weekly_p, plan_range_p, plan_year_st_p = convert_monthly_to_weekly_p(df_p_month, self.lot_size)

        # PSI Planner全体の計画開始年との整合性を確認
        assert plan_year_st_p == self.plan_year_st, (
            f"P data year start {plan_year_st_p} mismatches PSI plan start {self.plan_year_st}"
        )

        # ノード単位で週次 P_lot を登録
        set_df_Plots2psi4supply(self.nodes_outbound, df_weekly_p, self.plan_year_st)

        # Step 1.5: キャパシティ算出
        self.derive_weekly_capacity_from_plots()

        print(f"[INFO] Loaded P_month_data.csv → psi4supply populated for {len(df_weekly_p)} entries")

        # Step 2: S_lot → P_lot 割当処理
        for node_name in unique_nodes:  # node_name is DADxxx
            try:
                dad_node = self.nodes_outbound[node_name]

                # psi4demand から需要ロットを収集
                demand_map = {
                    w: dad_node.psi4demand[w][0]
                    for w in range(len(dad_node.psi4demand))
                    if dad_node.psi4demand[w][0]
                }

                # キャパシティ情報の存在確認
                if node_name not in self.weekly_cap_dict:
                    print(f"[WARNING] No weekly capacity data for node {node_name}")
                    continue

                supply_weeks = self.weekly_cap_dict[node_name]

                # perform_allocation 実行
                alloc_result, alloc_links, alloc_warn = perform_allocation(
                    node=dad_node,
                    demand_map=demand_map,
                    supply_weeks=supply_weeks
                )

                print(f"[INFO] Allocation completed for {node_name}: {len(alloc_links)} links")
                if alloc_warn:
                    print(f"[WARNING] Allocation issues for {node_name}:\n" + "\n".join(alloc_warn))

                def allocation_result_to_psi4supply(allocation_result):
                    max_week = max(allocation_result.keys(), default=0)
                    psi4supply = [[[], [], [], []] for _ in range(max_week + 1)]
                    for w, lots in allocation_result.items():
                        psi4supply[w][3] = lots
                    return psi4supply

                psi4supply = allocation_result_to_psi4supply(alloc_result)

                for w in range(1, self.plan_range * 53):
                    if w < len(psi4supply) and len(psi4supply[w][3]) > 0:
                        dad_node.psi4supply[w][3] = copy.deepcopy(psi4supply[w][3])

            except Exception as e:
                print(f"[ERROR] Allocation error for {node_name}: {e}")

    except Exception as e:
        print(f"[FATAL ERROR] Failed to process P_month_data.csv: {e}")
else:
    print("warning: P_month_data.csv is missing")
















            # **********************************************
            # Step 1: P_month_data.csv の読み込みと週次変換
            # **********************************************
            if "P_month_data.csv" in data_file_list:
                p_path = os.path.join(self.directory, "P_month_data.csv")
                df_p_month = pd.read_csv(p_path, encoding='utf-8-sig')

                unique_nodes = df_p_month["node_name"].unique()
                # unique_nodes are DADxxx nodes
                # with using
                # for dad_node_name in unique_nodes:




                # 月次→週次変換＆Lot ID生成（複数年対応）
                df_weekly_p, plan_range_p, plan_year_st_p = convert_monthly_to_weekly_p(df_p_month, self.lot_size)

                # PSI Planner全体の計画開始年との整合性を確認
                assert plan_year_st_p == self.plan_year_st, (
                    f"P data year start {plan_year_st_p} mismatches PSI plan start {self.plan_year_st}"
                )

                # ノード単位で週次 P_lot を登録
                set_df_Plots2psi4supply(self.nodes_outbound, df_weekly_p, self.plan_year_st)

                # Step 1.5: キャパシティ算出
                self.derive_weekly_capacity_from_plots()

                print(f"[INFO] Loaded P_month_data.csv → psi4supply populated for {len(df_weekly_p)} entries")
            else:
                print("warning: P_month_data.csv is missing")
                return

            # **********************************************
            # Step 2: S_lot → P_lot 割当処理の実行
            # **********************************************

            #for node_name, node in self.nodes_outbound.items(): 

            # DADxxx nodeのみ　P_month_data.csvからuniqueで取得
            for node_name in unique_nodes: # node_name is DADxxx
                dad_node = self.nodes_outbound[node_name]

                # psi4demand から需要ロットを収集
                demand_map = {
                    w: dad_node.psi4demand[w][0]
                    for w in range(len(dad_node.psi4demand))
                    if dad_node.psi4demand[w][0]
                }

                # キャパシティ情報の存在確認
                if node_name not in self.weekly_cap_dict:
                    print(f"[WARNING] No weekly capacity data for node {node_name}")
                    continue

                supply_weeks = self.weekly_cap_dict[node_name]

                # perform_allocation 実行
                alloc_result, alloc_links, alloc_warn = perform_allocation(
                    node=dad_node,
                    demand_map=demand_map,
                    supply_weeks=supply_weeks
                )

                print(f"[INFO] Allocation completed for {node_name}: {len(alloc_links)} links")
                if alloc_warn:
                    print(f"[WARNING] Allocation issues for {node_name}:\n" + "\n".join(alloc_warn))


# **********************************
# End of main ALLOCATION
# **********************************

                def allocation_result_to_psi4supply(allocation_result):
                    max_week = max(allocation_result.keys(), default=0)
                    # 0週目（ダミー）+ max_week 週分を list で初期化
                    psi4supply = [[[], [], [], []] for _ in range(max_week + 1)]
            
                    for w, lots in allocation_result.items():
                        psi4supply[w][3] = lots  # wはlist indexとして機能する（1〜max_week）
            
                    return psi4supply


                psi4supply = allocation_result_to_psi4supply(alloc_result)
                #psi4supply = allocation_result_to_psi4supply(allocation_result)

                print(f"Allocation completed for {node_name}")
                print( "allocated psi4supply", psi4supply )

                print( "BEFORE ALLOC dad_node.psi4supply", dad_node.psi4supply )


                for w in range(1, self.plan_range*53):
                    if w < len(psi4supply) and len(psi4supply[w][3])>0:

                        print("before dad_node.psi4supply[w][3]",w, dad_node.psi4supply[w][3])
                        dad_node.psi4supply[w][3] = copy.deepcopy(psi4supply[w][3])
                        print("after dad_node.psi4supply[w][3] psi4supply",dad_node.psi4supply[w][3], psi4supply[w][3])



                print( "allocated dad_node.psi4supply", dad_node.psi4supply )

                except Exception as e:
                    print(f"Error processing allocation for {node_name}: {e}")

            else:
                print("error: P_month_data.csv is missed")




# **********************************
# Another ALLOCATION logic
# **********************************
#
#* 「**紐付け方式**」：S\_lotとP\_lotを1対1対応で明示リンク
#* 「**流し込み方式**」：空いているP\_lotスロットにS\_lotを流し込む（順次・容量制限）
#
#という2つの考え方がある中で、**現状の `allocate_lots_to_harvest()` は後者（流し#込み）です。**
#
#---
#
#### 🧭 一般的なSCMパッケージとの比較：
#
#| 方法         | 特徴                                         | 一般性     |
#|       ------ | ----------------------                       | -----      |
#| 紐付け方式   | トレーサビリティが高い／ロット指定に有効     | B2B向き    |
#| 流し込み方式 | キャパシティに基づき順次割当て／高速処理可能 | 汎用性高い |
#
#---
#
#### 🔧 今後の方向としては：
#
#* 流し込みベースだが **割り当て後に S\_lot と P\_lot の「参照リンク」を持たせる**
#  → ハイブリッド方式（流し込み + トレース）も可能です
#
#---
#
#ご希望であれば、このような **「紐付け情報付き・流し込み方式」** の拡張 allocation ロジックも提示できます。いかがでしょうか？
#
#
## ****************************************************************
# 「紐付け情報付き・流し込み方式」 の拡張 allocation ロジック
# ****************************************************************
#
#S\_lot を空いている週の P\_lot に流し込みながら、\*\*どの S\_lot がどの P\_lot #に対応したかを明示的に記録（紐付け）\*\*します。
#
#---
#
### 🧩 `allocate_lots_with_links()`（紐付け付き・流し込み方式）
#
#```python
#from collections import defaultdict
#
#def allocate_lots_with_links(demand_lots_dict, supply_weeks, lot_capacity=1):
#    """
#    S_lots を P_lot スロットに順次流し込みながら、
#S_lot → P_lot の対応関係を記録。
#
#    Parameters:
#        demand_lots_dict (dict[int, list[str]]): 各週の S_lot ID の辞書（例: {week: [lot1, lot2]})
#        supply_weeks (list[dict]): P_lot の空き情報（例: [{"week": 1, "capacity": 3}, ...]）
#        lot_capacity (int): 各週のキャパ数（通常は1ロット1ユニット）
#
#    Returns:
#        allocation_result (dict[int, list[str]]): P_lot 側から見た割り当て結果（psi4supply[w][3]に相当）
#        allocation_links (dict[str, dict]): 各 S_lot → {"week": w, "linked_to": "P_lot_id"} のリンク情報
#        warnings (list[str]): 割当不能な場合の警告
#    """
#    allocation_result = defaultdict(list)
#    allocation_links = {}
#    week_capacity_map = {w["week"]: w["capacity"] for w in supply_weeks}
#    sorted_weeks = sorted(week_capacity_map.keys())
#    week_index = 0
#    warnings = []
#
#    # flatten all S_lots
#    all_s_lots = []
#    for lots in demand_lots_dict.values():
#        all_s_lots.extend(lots)
#
#    for s_lot in all_s_lots:
#        allocated = False
#        attempts = 0
#        while attempts < len(sorted_weeks):
#            week = sorted_weeks[week_index % len(sorted_weeks)]
#            if len(allocation_result[week]) < week_capacity_map[week]:
#                # 擬似的に P_lot_id を week+通し番号で生成
#                p_lot_id = f"P{week}_{len(allocation_result[week])+1:04d}"
#                allocation_result[week].append(s_lot)
#                allocation_links[s_lot] = {"week": week, "linked_to": p_lot_id}
#                allocated = True
#                break
#            week_index += 1
#            attempts += 1
#        if not allocated:
#            warnings.append(f"Cannot allocate S_lot {s_lot} — all weeks full")
#
#    return dict(allocation_result), allocation_links, warnings
#```
#
#---
#
### ✅ 戻り値の意味
#
#| 変数名              | 内容                                                 |
#| ------------------- | --------------------------------------------         |
#| allocation_result   | psi4supply[w][3]各週にどの S_lot が割当てられたか    |
#| allocation_links    | 各S_lotが"いつ""どの"仮想 P\_lot\_id に割当てられたか|
#| `warnings`          | 割当失敗した S\_lot の記録                           |
#
#
#---
#
### 📌 活用方法
#
#```python
#allocation_result, allocation_links, warnings = allocate_lots_with_links(demand_map, harvest_weeks)
#
## psi4supply 更新
#for w, s_lots in allocation_result.items():
#    node.psi4supply[w][3] = s_lots  # または extend など
#
## S_lot ごとの対応先の追跡が可能
#for s_lot, link_info in allocation_links.items():
#    print(f"{s_lot} was allocated to week {link_info['week']} as {link_info['linked_to']}")
#```
#
#---
#
### 🔧 拡張可能なポイント
#
#* `linked_to` に実際の `Lot` インスタンスを入れると P\_lot と S\_lot の双方向リ#ンクが可能
#* 週別に複数 SKU の同時割当てにも対応可能（SKU名をキーにするだけ）
#
#---
#
#ご希望に応じて：
#
#* `Lot` クラスを用いた双方向リンク化
#* GUI表示やログ出力の統合
#
#などの拡張も可能です。必要であれば続けて提案します。

# *************************************************************************



            # *******************************
            # EXIT allocation process
            # *******************************

            print("Data files loaded successfully.")



# **** A PART of ORIGINAL load_data_files *****


        def count_lots_on_S_psi4demand(node, S_list):
                if not node.children:
                        for w_psi in node.psi4demand:
                                S_list.append(w_psi[0])
                for child in node.children:
                        count_lots_on_S_psi4demand(child, S_list)
                return S_list

        S_list = []
        year_lots_list4S = []
        S_list = count_lots_on_S_psi4demand(root_node_outbound, S_list)

        #@250117 STOP
        #plan_year_st = year_st

        #for yyyy in range(plan_year_st, plan_year_st + plan_range + 1):
        for yyyy in range(int(plan_year_st), int(plan_year_st + plan_range + 1)):

                year_lots4S = count_lots_yyyy(S_list, str(yyyy))
                year_lots_list4S.append(year_lots4S)

        self.market_potential = year_lots_list4S[1]
        print("self.market_potential", self.market_potential)

        self.total_supply_plan = round(self.market_potential * self.target_share)
        print("self.total_supply_plan", self.total_supply_plan)

        for filename in os.listdir(directory):
                if filename.endswith(".csv"):
                        filepath = os.path.join(directory, filename)
                        print(f"Loading file: {filename}")
                        if "outbound" in filename.lower():
                                self.outbound_data.append(pd.read_csv(filepath))
                        elif "inbound" in filename.lower():
                                self.inbound_data.append(pd.read_csv(filepath))
        print("Outbound files loaded.")
        print("Inbound files loaded.")

        def find_node_with_cost_standard_flag(nodes, flag_value):
                for node_name, node in nodes.items():
                        if node.cost_standard_flag == flag_value:
                                return node_name, node
                return None, None

        node_name, base_leaf = find_node_with_cost_standard_flag(nodes_outbound, 100)
        self.base_leaf_name = node_name

        if node_name is None:
                print("NO cost_standard = 100 in profile")
        else:
                print(f"Node name: {node_name}, Base leaf: {base_leaf}")

        root_price = set_price_leaf2root(base_leaf, self.root_node_outbound, 100)
        print("root_price", root_price)
        set_value_chain_outbound(root_price, self.root_node_outbound)



        print("demand_planning execute")




        # *********************************
        # psi2i 4 demand
        # *********************************
        calc_all_psi2i4demand(self.root_node_outbound)



        # ********************************
        # PRE_SET decouple node before "supply" planning 
        # ********************************
        if not self.decouple_node_selected:
                nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound)
                print("nodes_decouple_all", nodes_decouple_all)
                decouple_node_names = nodes_decouple_all[-2]
        else:
                decouple_node_names = self.decouple_node_selected




        # *********************************
        # #@250626 TEST DATA DUMP4ALLOCATION
        # *********************************


        #@250705 MEMO 
        # 1. "total_supply"のchildren_listとしてDADxxxを抽出する
        # 2. for a_DAD_node in children_list:でDADxxx以降の計画を処理する


        total_supply_node = self.nodes_outbound["supply_point"] 

        DADs_list = total_supply_node.children

        print("DADs_list", DADs_list)

        for dad in DADs_list:

        
        #@250706 STOP
        #a_DAD_node.dump_PSI_psi4demand() # defined on tree.py
        #a_DAD_node = self.nodes_outbound["DADJPN"] 
        #a_DAD_node.dump_PSI_psi4demand() # defined on tree.py


        # ******************************************
        # confirmedSを出荷先ship2のPとSにshift&set
        # ******************************************
        # 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
        # main function is this: place_P_in_supply_LT(w, ship2node, lot)
        # ******************************************

        #@2500630 STOP
        ##feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)
        #feedback_psi_lists(a_DAD_node, self.nodes_outbound)
        

        #@250628 GO STOP
        #@250630 GO
        ##self.root_node_outbound.calcPS2I4supply()
        #
        #a_DAD_node.calcPS2I4supply()


            # This is DADs PS2I planning
            dad.calcPS2I4supply()


        #@250706 STOP
        #print("after a_DAD_node.calcPS2I4supply() is this")
        #a_DAD_node.dump_PSI_psi4demand() # defined on tree.py

        ##@250630 probe psi4supply[][]
        #a_DAD_node = self.nodes_outbound["DADJPN"] 
        #print("250630 probe psi4supply[][] after calcPS2I4supply", a_DAD_node.name, a_DAD_node.psi4supply)

     
        #@250630 STOP
        #self.update_evaluation_results()
        #self.decouple_node_selected = []
        #self.view_nx_matlib_stop_draw()




        #@250706 
        # "Demand Leveling"と先行生産は、需給バランス"Lot Allocation"の1つ
        # 今回の米のLot Allocationは初期load_datafilesの中で"P_lots"生成で実施

        #@250706 STOP
        #print("Demand Leveling execute")
        #year_st = self.plan_year_st
        #year_end = year_st + self.plan_range - 1
        #pre_prod_week = self.config.DEFAULT_PRE_PROC_LT
        ##pre_prod_week = self.pre_proc_LT



    # +++++++++++++++++++++++++++++++++++++++++++++++
    # Mother Plant demand leveling 
    # root_node_outbound /supply / [w][0] setting S_allocated&pre_prod&leveled
    # +++++++++++++++++++++++++++++++++++++++++++++++
        #demand_leveling_on_ship(self.root_node_outbound, pre_prod_week, year_st, year_end)



        #@250630 STOP
        #a_DAD_node.calcS2P_4supply()
        ##self.root_node_outbound.calcS2P_4supply()
        #


        #@25062829 STOP GO a_DAD_node
        #@250630 GO
        #self.root_node_outbound.calcPS2I4supply()
        #a_DAD_node.calcPS2I4supply()
        
        
        # ******************************************
        # confirmedSを出荷先ship2のPとSにshift&set
        # ******************************************
        # 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
        # main function is this: place_P_in_supply_LT(w, ship2node, lot)
        # ******************************************
        #feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)
        
        ##@250628 GO STOP
        #self.root_node_outbound.calcPS2I4supply()


        #@250630 STOP GO
        #self.update_evaluation_results()
        #self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')
        #self.view_nx_matlib_stop_draw()


        #@250630_0701 STOP 
        #print("Supply planning with Decoupling points")
        #self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')


        #@250706 STOP
        ##@250630 probe psi4supply[][]
        #a_DAD_node = self.nodes_outbound["DADJPN"] 
        #print("250630 probe psi4supply[][] 4 show_PSI", a_DAD_node.name, a_DAD_node.psi4supply)


        #@250706 STOP
        ## ********************************
        ## setting decouple node
        ## ********************************
        #if not self.decouple_node_selected:
        #        nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound)
        #        print("nodes_decouple_all", nodes_decouple_all)
        #        decouple_node_names = nodes_decouple_all[-2]
        #else:
        #        decouple_node_names = self.decouple_node_selected


        #@250706 STOP
        ##@250630_0701 STOP GO
        ##push_pull_all_psi2i_decouple4supply5(self.root_node_outbound, decouple_node_names)
        #push_pull_all_psi2i_decouple4supply5(a_DAD_node, decouple_node_names)


            # This is DADs PUSH&PULL planning
            push_pull_all_psi2i_decouple4supply5(dad, decouple_node_names)

        # *************************
        # End of DADs planning
        # *************************


        # eval area
        self.update_evaluation_results()


        # network area
        self.decouple_node_selected = decouple_node_names
        self.view_nx_matlib4opt()



        # PSI area
        #self.root.after(1000, self.show_psi("outbound", "supply"))

        self.root.after(1000, lambda: self.show_psi("outbound", "supply"))
        # lambda: にすることで、1000ms 後に初めて show_psi() を実行する
        # という本来の動きに


        # ****************************
        # market potential Graph viewing
        # ****************************
        self.initialize_parameters()




        # Enable buttons after loading is complete
        self.supply_planning_button.config(state="normal")
        self.eval_buffer_stock_button.config(state="normal")
        print("Data files loaded and buttons enabled.")




        #try:
        #    # Perform data-loading steps
        #    self.root.update_idletasks()  # Ensure the GUI is updated during the process
        #
        #    # Assume data is successfully loaded
        #    print("Data loaded successfully!")
        #
        #    # Re-enable buttons
        #    self.supply_planning_button.config(state="normal")
        #    self.eval_buffer_stock_button.config(state="normal")
        #
        #except Exception as e:
        #    print(f"Error during data loading: {e}")
        #    tk.messagebox.showerror("Error", "Failed to load data files.")


        # Return focus to the main window
        self.root.focus_force()






# **** A PART of ORIGINAL load_data_files END *****





    def load_data_files_OLD(self):
        directory = filedialog.askdirectory(title="Select Data Directory")

        if directory:
            try:
                self.lot_size = int(self.lot_size_entry.get())
                self.plan_year_st = int(self.plan_year_entry.get())
                self.plan_range = int(self.plan_range_entry.get())
            except ValueError:
                print("Invalid input for lot size, plan year start, or plan range. Using default values.")

            self.outbound_data = []
            self.inbound_data = []

            data_file_list = os.listdir(directory)

            self.directory = directory
            self.load_directory = directory

            if "profile_tree_outbound.csv" in data_file_list:
                file_path = os.path.join(directory, "profile_tree_outbound.csv")
                nodes_outbound = {}
                nodes_outbound, root_node_name_out = create_tree_set_attribute(file_path)
                root_node_outbound = nodes_outbound[root_node_name_out]

                def make_leaf_nodes(node, leaf_list):
                    if not node.children:
                        leaf_list.append(node.name)
                    for child in node.children:
                        make_leaf_nodes(child, leaf_list)
                    return leaf_list

                leaf_nodes_out = make_leaf_nodes(root_node_outbound, [])
                self.nodes_outbound = nodes_outbound
                self.root_node_outbound = root_node_outbound
                self.leaf_nodes_out = leaf_nodes_out
                set_positions(root_node_outbound)
                set_parent_all(root_node_outbound)
                print_parent_all(root_node_outbound)
            else:
                print("error: profile_tree_outbound.csv is missed")

            if "profile_tree_inbound.csv" in data_file_list:
                file_path = os.path.join(directory, "profile_tree_inbound.csv")
                nodes_inbound = {}
                nodes_inbound, root_node_name_in = create_tree_set_attribute(file_path)
                root_node_inbound = nodes_inbound[root_node_name_in]
                self.nodes_inbound = nodes_inbound
                self.root_node_inbound = root_node_inbound
                set_positions(root_node_inbound)
                set_parent_all(root_node_inbound)
                print_parent_all(root_node_inbound)
            else:
                print("error: profile_tree_inbound.csv is missed")

            if "node_cost_table_outbound.csv" in data_file_list:
                file_path = os.path.join(directory, "node_cost_table_outbound.csv")
                read_set_cost(file_path, nodes_outbound)
            else:
                print("error: node_cost_table_outbound.csv is missed")

            if "node_cost_table_inbound.csv" in data_file_list:
                file_path = os.path.join(directory, "node_cost_table_inbound.csv")
                read_set_cost(file_path, nodes_inbound)
            else:
                print("error: node_cost_table_inbound.csv is missed")


            if "S_month_data.csv" in data_file_list:
                in_file_path = os.path.join(directory, "S_month_data.csv")

                df_weekly, plan_range, plan_year_st = process_monthly_demand(in_file_path, self.lot_size)

                #df_weekly, plan_range, plan_year_st = trans_month2week2lot_id_list(in_file_path, self.lot_size)


                self.plan_year_st = plan_year_st
                self.plan_range = plan_range
                self.plan_year_entry.delete(0, tk.END)
                self.plan_year_entry.insert(0, str(self.plan_year_st))
                self.plan_range_entry.delete(0, tk.END)
                self.plan_range_entry.insert(0, str(self.plan_range))
                out_file_path = os.path.join(directory, "S_iso_week_data.csv")

                df_weekly.to_csv(out_file_path, index=False)

            else:
                print("error: S_month_data.csv is missed")




            root_node_outbound.set_plan_range_lot_counts(plan_range, plan_year_st)
            root_node_inbound.set_plan_range_lot_counts(plan_range, plan_year_st)

            node_psi_dict_Ot4Dm = make_psi_space_dict(root_node_outbound, {}, plan_range)
            node_psi_dict_Ot4Sp = make_psi_space_dict(root_node_outbound, {}, plan_range)
            self.node_psi_dict_In4Dm = make_psi_space_dict(root_node_inbound, {}, plan_range)
            self.node_psi_dict_In4Sp = make_psi_space_dict(root_node_inbound, {}, plan_range)
            set_dict2tree_psi(root_node_outbound, "psi4demand", node_psi_dict_Ot4Dm)
            set_dict2tree_psi(root_node_outbound, "psi4supply", node_psi_dict_Ot4Sp)
            set_dict2tree_psi(root_node_inbound, "psi4demand", self.node_psi_dict_In4Dm)
            set_dict2tree_psi(root_node_inbound, "psi4supply", self.node_psi_dict_In4Sp)




            # **********************************
            # make&set weekly demand "Slots" on leaf_node, propagate2root
            # initial setting psi4"demand"[w][0] to psi4"supply"[w][0]
            # **********************************
            #set_df_Slots2psi4demand(self.root_node_outbound, df_weekly)
            set_df_Slots2psi4demand(root_node_outbound, df_weekly)

            print("Data files loaded successfully.")





# **** A PART of ORIGINAL load_data_files *****

        def count_lots_on_S_psi4demand(node, S_list):
                if not node.children:
                        for w_psi in node.psi4demand:
                                S_list.append(w_psi[0])
                for child in node.children:
                        count_lots_on_S_psi4demand(child, S_list)
                return S_list

        S_list = []
        year_lots_list4S = []
        S_list = count_lots_on_S_psi4demand(root_node_outbound, S_list)

        #@250117 STOP
        #plan_year_st = year_st

        #for yyyy in range(plan_year_st, plan_year_st + plan_range + 1):
        for yyyy in range(int(plan_year_st), int(plan_year_st + plan_range + 1)):

                year_lots4S = count_lots_yyyy(S_list, str(yyyy))
                year_lots_list4S.append(year_lots4S)

        self.market_potential = year_lots_list4S[1]
        print("self.market_potential", self.market_potential)

        self.total_supply_plan = round(self.market_potential * self.target_share)
        print("self.total_supply_plan", self.total_supply_plan)

        for filename in os.listdir(directory):
                if filename.endswith(".csv"):
                        filepath = os.path.join(directory, filename)
                        print(f"Loading file: {filename}")
                        if "outbound" in filename.lower():
                                self.outbound_data.append(pd.read_csv(filepath))
                        elif "inbound" in filename.lower():
                                self.inbound_data.append(pd.read_csv(filepath))
        print("Outbound files loaded.")
        print("Inbound files loaded.")

        def find_node_with_cost_standard_flag(nodes, flag_value):
                for node_name, node in nodes.items():
                        if node.cost_standard_flag == flag_value:
                                return node_name, node
                return None, None

        node_name, base_leaf = find_node_with_cost_standard_flag(nodes_outbound, 100)
        self.base_leaf_name = node_name

        if node_name is None:
                print("NO cost_standard = 100 in profile")
        else:
                print(f"Node name: {node_name}, Base leaf: {base_leaf}")

        root_price = set_price_leaf2root(base_leaf, self.root_node_outbound, 100)
        print("root_price", root_price)
        set_value_chain_outbound(root_price, self.root_node_outbound)



        print("demand_planning execute")




        # *********************************
        # psi2i 4 demand
        # *********************************
        calc_all_psi2i4demand(self.root_node_outbound)


        # *********************************
        # #@250626 TEST DATA DUMP4ALLOCATION
        # *********************************

        a_DAD_node = self.nodes_outbound["DADJPN"] 

        a_DAD_node.dump_S_psi4demand() # defined on tree.py



        # ******************************************
        # confirmedSを出荷先ship2のPとSにshift&set
        # ******************************************
        # 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
        # main function is this: place_P_in_supply_LT(w, ship2node, lot)
        # ******************************************

        feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)
        #feedback_psi_lists(a_DAD_node, self.nodes_outbound)
        
        #@250628 GO STOP
        self.root_node_outbound.calcPS2I4supply()
        #a_DAD_node.calcPS2I4supply()




        self.update_evaluation_results()
        self.decouple_node_selected = []
        self.view_nx_matlib_stop_draw()





        print("Demand Leveling execute")
        year_st = self.plan_year_st
        year_end = year_st + self.plan_range - 1
        pre_prod_week = self.config.DEFAULT_PRE_PROC_LT
        #pre_prod_week = self.pre_proc_LT



    # +++++++++++++++++++++++++++++++++++++++++++++++
    # Mother Plant demand leveling 
    # root_node_outbound /supply / [w][0] setting S_allocated&pre_prod&leveled
    # +++++++++++++++++++++++++++++++++++++++++++++++
        demand_leveling_on_ship(self.root_node_outbound, pre_prod_week, year_st, year_end)

        self.root_node_outbound.calcS2P_4supply()

        #@250628 STOP
        #self.root_node_outbound.calcPS2I4supply()
        
        
        # ******************************************
        # confirmedSを出荷先ship2のPとSにshift&set
        # ******************************************
        # 出荷先node psiのPとSに、confirmed_SのlotsをLT shiftで置く
        # main function is this: place_P_in_supply_LT(w, ship2node, lot)
        # ******************************************
        feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)
        
        #@250628 GO
        self.root_node_outbound.calcPS2I4supply()


        self.update_evaluation_results()
        self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')
        self.view_nx_matlib_stop_draw()



        print("Supply planning with Decoupling points")
        self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')

        if not self.decouple_node_selected:
                nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound)
                print("nodes_decouple_all", nodes_decouple_all)
                decouple_node_names = nodes_decouple_all[-2]
        else:
                decouple_node_names = self.decouple_node_selected




        push_pull_all_psi2i_decouple4supply5(self.root_node_outbound, decouple_node_names)
        #push_pull_all_psi2i_decouple4supply5(a_DAD_node, decouple_node_names)


        # eval area
        self.update_evaluation_results()


        # network area
        self.decouple_node_selected = decouple_node_names
        self.view_nx_matlib4opt()



        # PSI area
        self.root.after(1000, self.show_psi("outbound", "supply"))



        # ****************************
        # market potential Graph viewing
        # ****************************
        self.initialize_parameters()




        # Enable buttons after loading is complete
        self.supply_planning_button.config(state="normal")
        self.eval_buffer_stock_button.config(state="normal")
        print("Data files loaded and buttons enabled.")




        #try:
        #    # Perform data-loading steps
        #    self.root.update_idletasks()  # Ensure the GUI is updated during the process
        #
        #    # Assume data is successfully loaded
        #    print("Data loaded successfully!")
        #
        #    # Re-enable buttons
        #    self.supply_planning_button.config(state="normal")
        #    self.eval_buffer_stock_button.config(state="normal")
        #
        #except Exception as e:
        #    print(f"Error during data loading: {e}")
        #    tk.messagebox.showerror("Error", "Failed to load data files.")


        # Return focus to the main window
        self.root.focus_force()






# **** A PART of ORIGINAL load_data_files END *****


# **** call_backs *****


    def save_data(self, save_directory):

        print(f"保存前 - market_potential: {self.market_potential}, target_share: {self.target_share}")  # ログ追加

        print(f"保存前 - total_revenue : {self.total_revenue}, total_profit : {self.total_profit}")  

        psi_planner_app_save = PSIPlannerApp4save()
        psi_planner_app_save.update_from_psiplannerapp(self)

        print(f"保存時 - market_potential: {psi_planner_app_save.market_potential}, target_share: {psi_planner_app_save.target_share}")  # ログ追加

        print(f"保存時 - total_revenue: {psi_planner_app_save.total_revenue}, total_profit: {psi_planner_app_save.total_profit}")  




        with open(os.path.join(save_directory, 'psi_planner_app.pkl'), "wb") as f:
            pickle.dump(psi_planner_app_save.__dict__, f)
        print("データを保存しました。")




    def save_to_directory(self):
        # 1. Save先となるdirectoryの問い合わせ
        save_directory = filedialog.askdirectory()

        if not save_directory:
            return  # ユーザーがキャンセルした場合

        # 2. 初期処理のcsv fileのコピー
        for filename in os.listdir(self.directory):
            if filename.endswith('.csv'):
                full_file_name = os.path.join(self.directory, filename)
                if os.path.isfile(full_file_name):
                    shutil.copy(full_file_name, save_directory)


        # 3. Tree構造の保存
        with open(os.path.join(save_directory, 'root_node_outbound.pkl'), 'wb') as f:
            pickle.dump(self.root_node_outbound, f)
            print(f"root_node_outbound saved: {self.root_node_outbound}")

        with open(os.path.join(save_directory, 'root_node_inbound.pkl'), 'wb') as f:
            pickle.dump(self.root_node_inbound, f)
            print(f"root_node_inbound saved: {self.root_node_inbound}")

        with open(os.path.join(save_directory, 'root_node_out_opt.pkl'), 'wb') as f:
            pickle.dump(self.root_node_out_opt, f)
            print(f"root_node_out_opt saved: {self.root_node_out_opt}")


        # 4. グラフデータの保存
        nx.write_gml(self.G, f"{save_directory}/G.gml")
        nx.write_gml(self.Gdm_structure, f"{save_directory}/Gdm_structure.gml")
        nx.write_gml(self.Gsp, f"{save_directory}/Gsp.gml")
        print(f"グラフが{save_directory}に保存されました")

        nx.write_gpickle(self.G, os.path.join(save_directory, 'G.gpickle'))
        nx.write_gpickle(self.Gdm_structure, os.path.join(save_directory, 'Gdm_structure.gpickle'))
        nx.write_gpickle(self.Gsp, os.path.join(save_directory, 'Gsp.gpickle'))
        print("Graph data saved.")



        # saveの前にself.market_potential,,,をupdate

        #self.initialize_parameters()
        self.updated_parameters()

        # 5. PSIPlannerAppのデータ・インスタンスの保存
        self.save_data(save_directory)

        # 追加：ファイルの存在とサイズの確認
        for filename in ['root_node_outbound.pkl', 'root_node_inbound.pkl', 'psi_planner_app.pkl']:
            full_file_name = os.path.join(save_directory, filename)
            if os.path.exists(full_file_name):
                file_size = os.path.getsize(full_file_name)
                print(f"{filename} exists, size: {file_size} bytes")
            else:
                print(f"{filename} does not exist")

        # 6. 完了メッセージの表示
        messagebox.showinfo("Save Completed", "Plan data save is completed")





    def load_data(self, load_directory):
        with open(os.path.join(load_directory, 'psi_planner_app.pkl'), "rb") as f:
            loaded_attributes = pickle.load(f)

    #@ STOP this is a sample code for "fixed file"
    #def load_data(self, filename="saved_data.pkl"):
    #    with open(filename, "rb") as f:
    #        loaded_attributes = pickle.load(f)


        psi_planner_app_save = PSIPlannerApp4save()
        psi_planner_app_save.__dict__.update(loaded_attributes)
        
        # 選択的にインスタンス変数を更新
        self.root_node = psi_planner_app_save.root_node


        #@ STOP
        #self.D_S_flag = psi_planner_app_save.D_S_flag
        #self.week_start = psi_planner_app_save.week_start
        #self.week_end = psi_planner_app_save.week_end

        self.decouple_node_selected=psi_planner_app_save.decouple_node_selected


        self.G = psi_planner_app_save.G
        self.Gdm = psi_planner_app_save.Gdm
        self.Gdm_structure = psi_planner_app_save.Gdm_structure
        self.Gsp = psi_planner_app_save.Gsp
        self.pos_E2E = psi_planner_app_save.pos_E2E

        self.total_revenue = psi_planner_app_save.total_revenue
        print("load_data: self.total_revenue", self.total_revenue)
        self.total_profit = psi_planner_app_save.total_profit
        print("load_data: self.total_profit", self.total_profit)

        self.flowDict_opt = psi_planner_app_save.flowDict_opt
        self.flowCost_opt = psi_planner_app_save.flowCost_opt


        self.market_potential = psi_planner_app_save.market_potential
        print("self.market_potential", self.market_potential)

        self.target_share = psi_planner_app_save.target_share
        print("self.target_share", self.target_share)

        # エントリウィジェットに反映する
        self.ts_entry.delete(0, tk.END)
        self.ts_entry.insert(0, f"{self.target_share * 100:.0f}")  # 保存された値を反映



        print(f"読み込み時 - market_potential: {self.market_potential}, target_share: {self.target_share}")  # ログ追加
        print("データをロードしました。")





    def regenerate_nodes(self, root_node):
        nodes = {}

        def traverse(node):
            nodes[node.name] = node
            for child in node.children:
                traverse(child)

        traverse(root_node)
        return nodes





    def load_from_directory(self):
        # 1. Load元となるdirectoryの問い合わせ
        load_directory = filedialog.askdirectory()

        if not load_directory:
            return  # ユーザーがキャンセルした場合

        # 2. Tree構造の読み込み
        self.load_directory = load_directory
        self.directory      = load_directory # for "optimized network"
        self._load_tree_structure(load_directory)








        # 3. PSIPlannerAppのデータ・インスタンスの読み込み
        self.load_data(load_directory)

        # if "save files" are NOT optimized one
        if os.path.exists(f"{load_directory}/root_node_out_opt.pkl"):
            pass
        else:
            self.flowDict_opt = {}  # NO optimize



        ## 3. PSIPlannerAppのデータ・インスタンスの読み込みと更新
        #self.selective_update(load_directory)


        # 4. nodes_outboundとnodes_inboundを再生成
        self.nodes_outbound = self.regenerate_nodes(self.root_node_outbound)
        self.nodes_inbound = self.regenerate_nodes(self.root_node_inbound)

        #self.nodes_out_opt = self.regenerate_nodes(self.root_node_out_opt)


        print("load_from_directory self.decouple_node_selected", self.decouple_node_selected)





        #@241224 ADD
        # eval area
        self.update_evaluation_results()


        ## 5. ネットワークグラフの描画
        #self.draw_networkx_graph()

        #@ STOP RUN change2OPT
        # 5. ネットワークグラフの描画

        self.view_nx_matlib4opt()

        #self.view_nx_matlib()


        #@ MOVED
        self.updated_parameters()


        #@ STOP RUN
        # 6. PSIの表示
        if self.root_node_out_opt == None:
            self.root.after(1000, self.show_psi("outbound", "supply"))

            #@ STOP
            ## パラメータの初期化と更新を呼び出し
            #self.updated_parameters()

        else:  # is root_node_out_opt
            self.root.after(1000, self.show_psi_graph4opt)


            #@ STOP
            ## パラメータの初期化と更新を呼び出し
            #self.set_market_potential(self.root_node_out_opt)
            #self.updated_parameters()
            ##self.initialize_parameters()

        # 7. 完了メッセージの表示
        messagebox.showinfo("Load Completed", "Plan data load is completed")




    def on_exit(self):
        # 確認ダイアログの表示
        if messagebox.askokcancel("Quit", "Do you really want to exit?"):
            # 全てのスレッドを終了
            for thread in threading.enumerate():
                if thread is not threading.main_thread():
                    thread.join(timeout=1)
    
            #for widget in self.root.winfo_children():
            #    widget.destroy()
    
            #self.root.destroy()
            self.root.quit()


    # **********************************
    # sub menus
    # **********************************


    # viewing Cost Stracture / an image of Value Chain
    def show_cost_stracture_bar_graph(self):
        try:
            if self.root_node_outbound is None or self.root_node_inbound is None:
                raise ValueError("Data has not been loaded yet")
            
            self.show_nodes_cs_lot_G_Sales_Procure(self.root_node_outbound, self.root_node_inbound)
        
        except ValueError as ve:
            print(f"error: {ve}")
            tk.messagebox.showerror("error", str(ve))
        
        except AttributeError:
            print("Error: Required attributes are missing from the node. Please check if the data is loaded.")
            tk.messagebox.showerror("Error", "Required attributes are missing from the node. Please check if the data is loaded.")
        
        except Exception as e:
            print(f"An unexpected error has occurred: {e}")
            tk.messagebox.showerror("Error", f"An unexpected error has occurred: {e}")




    def show_nodes_cs_lot_G_Sales_Procure(self, root_node_outbound, root_node_inbound):
        attributes = [
            'cs_direct_materials_costs',
            'cs_marketing_promotion',
            'cs_sales_admin_cost',
            'cs_tax_portion',
            'cs_logistics_costs',
            'cs_warehouse_cost',
            'cs_prod_indirect_labor',
            'cs_prod_indirect_others',
            'cs_direct_labor_costs',
            'cs_depreciation_others',
            'cs_profit',
        ]

        def dump_node_amt_all_in(node, node_amt_all):
            for child in node.children:
                dump_node_amt_all_in(child, node_amt_all)
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_IN"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            return node_amt_all

        def dump_node_amt_all_out(node, node_amt_all):
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_OUT"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            for child in node.children:
                dump_node_amt_all_out(child, node_amt_all)
            return node_amt_all

        node_amt_sum_in = dump_node_amt_all_in(root_node_inbound, {})
        node_amt_sum_out = dump_node_amt_all_out(root_node_outbound, {})
        node_amt_sum_in_out = {**node_amt_sum_in, **node_amt_sum_out}

        print("node_amt_sum_out", node_amt_sum_out)

        make_stack_bar4cost_stracture(node_amt_sum_out)

        # CSVファイルへのエクスポートを呼び出す
        self.export_cost_structure_to_csv(root_node_outbound, root_node_inbound, "cost_structure.csv")


        ## 供給配分の最適化 DADxxx2leaf_nodes profit_ratio CSVファイル
        #self.calculate_net_profit_rates(root_node_outbound)



    def export_cost_structure_to_csv(self, root_node_outbound, root_node_inbound, file_path):
        attributes = [
            'cs_direct_materials_costs',
            'cs_marketing_promotion',
            'cs_sales_admin_cost',
            'cs_tax_portion',
            'cs_logistics_costs',
            'cs_warehouse_cost',
            'cs_prod_indirect_labor',
            'cs_prod_indirect_others',
            'cs_direct_labor_costs',
            'cs_depreciation_others',
            'cs_profit',
        ]

        def dump_node_amt_all_in(node, node_amt_all):
            for child in node.children:
                dump_node_amt_all_in(child, node_amt_all)
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_IN"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            return node_amt_all

        def dump_node_amt_all_out(node, node_amt_all):
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_OUT"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            for child in node.children:
                dump_node_amt_all_out(child, node_amt_all)
            return node_amt_all

        node_amt_sum_in = dump_node_amt_all_in(root_node_inbound, {})
        node_amt_sum_out = dump_node_amt_all_out(root_node_outbound, {})
        node_amt_sum_in_out = {**node_amt_sum_in, **node_amt_sum_out}

        # 横持ちでデータフレームを作成
        data = []
        for node_name, costs in node_amt_sum_in_out.items():
            row = [node_name] + [costs[attr] for attr in attributes]
            data.append(row)

        df = pd.DataFrame(data, columns=["node_name"] + attributes)

        # CSVファイルにエクスポート
        df.to_csv(file_path, index=False)
        print(f"Cost structure exported to {file_path}")

        # leaf_nodes list is this
        print(self.leaf_nodes_out)



    def Save_Objective_Value(self):

        # 供給配分の最適化 DADxxx2leaf_nodes profit_ratio CSVファイル
        self.calculate_net_profit_rates(self.root_node_outbound)


    def calculate_net_profit_rates(self, root_node_outbound, output_file="net_profit_ratio.csv"):
        # **** 対象コスト項目
        target_cost_attributes = [

            'cs_cost_total'

            #'cs_logistics_costs',
            #'cs_warehouse_cost',
            #'cs_sales_admin_cost',
            #'cs_marketing_promotion'

        ]

        results = []



        ## Cost Structure
        #self.cs_price_sales_shipped = 0
        #self.cs_cost_total = 0
        #self.cs_profit = 0
        #self.cs_marketing_promotion = 0 #<=
        #self.cs_sales_admin_cost = 0    #<=
        #self.cs_SGA_total = 0

        ##self.cs_custom_tax = 0 # stop tariff_rate

        #self.cs_tax_portion = 0             #
        #self.cs_logistics_costs = 0         #
        #self.cs_warehouse_cost = 0          #
        #self.cs_direct_materials_costs = 0  #
        #self.cs_purchase_total_cost = 0
        #self.cs_prod_indirect_labor = 0     #
        #self.cs_prod_indirect_others = 0    #
        #self.cs_direct_labor_costs = 0      #
        #self.cs_depreciation_others = 0     #
        #self.cs_manufacturing_overhead = 0


        for leaf_name in self.leaf_nodes_out:

            node = self.nodes_outbound[leaf_name]
            #node = nodes_outbound.get(leaf_name)

            print(f"Checking init node: {node.name}")

            total_cost = 0.0
            total_profit = 0.0

            # **** ルート探索：Leaf Nodeからrootまで遡る

            while node is not None:
            #while node.name != "supply_point":
                print(f"Checking node: {node.name}")
                #for attr in target_cost_attributes:
                #    if not hasattr(node, attr):
                #        print(f"⚠️ 属性 {attr} がノード {node.name} に存在しません")
                #    total_cost += getattr(node, attr, 0.0)

                total_cost   += getattr(node, 'cs_cost_total', 0.0)
                total_profit += getattr(node, 'cs_profit', 0.0)


                # 親が"supply_point"なら、これ以上遡らずに終了
                print("node.parent.name", node.parent.name)
                if node.parent and node.parent.name == "supply_point":
                    #node = None
                    break
                else:
                    node = node.parent


                ## DADxxxのノードで停止する
                #if node.parent is None or "DAD" in node.parent.name:
                #    node = None
                #else:
                #    node = node.parent

                #node = node.parent
                        
            

            #while node is not None:
            #    for attr in target_cost_attributes:
            #        total_cost += getattr(node, attr, 0.0)
            #    total_profit += getattr(node, 'cs_profit', 0.0)
            #    node = node.parent

            # **** 純利益率計算
            total_amount = total_cost + total_profit
            net_profit_rate = total_profit / total_amount if total_amount > 0 else 0.0

            results.append({

                "Source": node.name,
                #"Source": root_node_outbound.name,

                "Target": leaf_name,
                "Total_Cost": round(total_cost, 4),
                "Total_Profit": round(total_profit, 4),
                "Net_Profit_Rate": round(net_profit_rate, 4)
            })

        # **** DataFrame化とCSV出力
        df_result = pd.DataFrame(results)

        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合


        df_result.to_csv(save_path, index=False)
        #df_result.to_csv(output_file, index=False)

        print(f"✔ 純利益率データを出力しました：{save_path}")




    def show_month_data_csv(self):
        pass
    

    def outbound_psi_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        # planの出力期間をcalculation
        output_period_outbound = 53 * self.root_node_outbound.plan_range

        # dataの収集
        data = []

        def collect_data(node, output_period):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                row = [node.name, attr]
                for week_no in range(output_period):
                    count = len(node.psi4supply[week_no][attr])
                    row.append(count)
                data.append(row)
            for child in node.children:
                collect_data(child, output_period)

        # root_node_outboundのtree構造を走査してdataを収集
        headers_outbound = ["node_name", "PSI_attribute"] + [f"w{i+1}" for i in range(output_period_outbound)]
        collect_data(self.root_node_outbound, output_period_outbound)

        # dataフレームを作成してCSVファイルに保存
        df_outbound = pd.DataFrame(data[:len(data)], columns=headers_outbound)  
        # STOP
        # # 複数のdataフレームを1つにaggregateする場合
        # df_combined = pd.concat([df_outbound, df_inbound])

        df_outbound.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"PSI data has been exported to {save_path}")




    def outbound_lot_by_lot_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        # 計画の出力期間を計算
        #output_period_outbound = 53 * self.plan_range
        output_period_outbound = 53 * self.root_node_outbound.plan_range

        start_year = self.plan_year_st

        # ヘッダーの作成
        headers = ["tier", "node_name", "parent", "PSI_attribute", "year", "week_no", "lot_id"]

        # データの収集
        data = []

        def collect_data(node, output_period, tier_no, parent_name):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                for week_no in range(output_period):
                    year = start_year + week_no // 53
                    week = week_no % 53 + 1
                    lot_ids = node.psi4supply[week_no][attr]
                    if not lot_ids:  # 空リストの場合、空文字を追加
                        lot_ids = [""]
                    for lot_id in lot_ids:
                        data.append([tier_no, node.name, parent_name, attr, year, week, lot_id])
            for child in node.children:
                collect_data(child, output_period, tier_no + 1, node.name)

        # root_node_outboundのツリー構造を走査してデータを収集
        collect_data(self.root_node_outbound, output_period_outbound, 0, "root")

        # データフレームを作成してCSVファイルに保存
        df = pd.DataFrame(data, columns=headers)
        df.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"Lot by Lot data has been exported to {save_path}")
    




#    def inbound_psi_to_csv(self):
#        pass
#    
#    def inbound_lot_by_lot_to_csv(self):
#        pass
#    
#    def lot_cost_structure_to_csv(self):
#        pass
#    
#    def supplychain_performance_to_csv(self):
#        pass
#    
#    def psi_for_excel(self):
#        pass
#    


    def inbound_psi_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        # planの出力期間をcalculation
        output_period_inbound = 53 * self.root_node_inbound.plan_range

        # dataの収集
        data = []

        def collect_data(node, output_period):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                row = [node.name, attr]
                for week_no in range(output_period):
                    count = len(node.psi4supply[week_no][attr])
                    row.append(count)
                data.append(row)
            for child in node.children:
                collect_data(child, output_period)

        # root_node_inboundのtree構造を走査してdataを収集
        headers_inbound = ["node_name", "PSI_attribute"] + [f"w{i+1}" for i in range(output_period_inbound)]
        collect_data(self.root_node_inbound, output_period_inbound)


        # dataフレームを作成してCSVファイルに保存
        df_inbound = pd.DataFrame(data[:len(data)], columns=headers_inbound) 

        df_inbound.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"PSI data has been exported to {save_path}")





    def inbound_lot_by_lot_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        # planの出力期間をcalculation
        output_period_inbound = 53 * self.root_node_inbound.plan_range
        start_year = self.plan_year_st

        # ヘッダーの作成
        headers = ["tier", "node_name", "parent", "PSI_attribute", "year", "week_no", "lot_id"]

        # dataの収集
        data = []

        def collect_data(node, output_period, tier_no, parent_name):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                for week_no in range(output_period):
                    year = start_year + week_no // 53
                    week = week_no % 53 + 1
                    lot_ids = node.psi4supply[week_no][attr]
                    if not lot_ids:  # 空リストの場合、空文字を追加
                        lot_ids = [""]
                    for lot_id in lot_ids:
                        data.append([tier_no, node.name, parent_name, attr, year, week, lot_id])
            for child in node.children:
                collect_data(child, output_period, tier_no + 1, node.name)

        # root_node_outboundのtree構造を走査してdataを収集
        collect_data(self.root_node_inbound, output_period_inbound, 0, "root")

        # dataフレームを作成してCSVファイルに保存
        df = pd.DataFrame(data, columns=headers)
        df.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"Lot by Lot data has been exported to {save_path}")








    def lot_cost_structure_to_csv(self):
        # "PSI for Excel"のprocess内容を定義

        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        self.export_cost_structure_to_csv(self.root_node_outbound, self.root_node_inbound, save_path)


        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"export_cost_structure_to_csv data has been exported to {save_path}")








    def show_cost_structure_bar_graph(self):
        try:
            if self.root_node_outbound is None or self.root_node_inbound is None:
                raise ValueError("Data has not been loaded yet")

            show_nodes_cs_lot_G_Sales_Procure(self.root_node_outbound, self.root_node_inbound)
        
        except ValueError as ve:
            print(f"error: {ve}")
            tk.messagebox.showerror("error", str(ve))
        
        except AttributeError:
            print("Error: Required attributes are missing from the node. Please check if the data is loaded.")
            tk.messagebox.showerror("Error", "Required attributes are missing from the node. Please check if the data is loaded.")
        
        except Exception as e:
            print(f"An unexpected error has occurred: {e}")
            tk.messagebox.showerror("Error", f"An unexpected error has occurred: {e}")




    def outbound_rev_prof_csv(self):
        # "PSI for Excel"のprocess内容を定義
        pass



    def supplychain_performance_to_csv(self):
        # ファイル保存ダイアログを表示して保存先ファイルパスを取得
        save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not save_path:
            return  # ユーザーがキャンセルした場合

        self.export_performance_to_csv(self.root_node_outbound, self.root_node_inbound, save_path)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"Business performance data has been exported to {save_path}")


    def export_performance_to_csv(self, root_node_outbound, root_node_inbound, file_path):
        attributes = [


# evaluated cost = Cost Structure X lot_counts


            #@250322 STOP
            #"cs_custom_tax",             # political TAX parameter
            # "cs_WH_cost_coefficiet",    # operational cost parameter


            # "purchase_total_cost" is followings
            "cs_direct_materials_costs", # material
            "cs_tax_portion",            # portion calculated by TAX xx%
            "cs_logistics_costs",        # inbound logistic cost

            # plant operations are followings
            "cs_warehouse_cost",

            # eval_cs_manufacturing_overhead
            "cs_prod_indirect_labor",    # man indirect
            "cs_prod_indirect_others",   # expense
            "cs_direct_labor_costs",     # man direct
            "cs_depreciation_others",    # machine

            # Sales side operations
            "cs_marketing_promotion",
            "cs_sales_admin_cost",

            # cash generated
            "cs_profit",

            # sub total cost item
            "cs_purchase_total_cost",    # material + TAX + logi cost
            "cs_manufacturing_overhead",
            "cs_SGA_total",  # marketing_promotion + sales_admin_cost

            "cs_cost_total",
            "cs_price_sales_shipped", # revenue
        ]


        def dump_node_amt_all_in(node, node_amt_all):
            for child in node.children:
                dump_node_amt_all_in(child, node_amt_all)
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_IN"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            return node_amt_all

        def dump_node_amt_all_out(node, node_amt_all):
            amt_list = {attr: getattr(node, attr) for attr in attributes}
            if node.name == "JPN":
                node_amt_all["JPN_OUT"] = amt_list
            else:
                node_amt_all[node.name] = amt_list
            for child in node.children:
                dump_node_amt_all_out(child, node_amt_all)
            return node_amt_all

        node_amt_sum_in = dump_node_amt_all_in(root_node_inbound, {})
        node_amt_sum_out = dump_node_amt_all_out(root_node_outbound, {})
        node_amt_sum_in_out = {**node_amt_sum_in, **node_amt_sum_out}

        # 横持ちでdataフレームを作成
        data = []
        for node_name, performance in node_amt_sum_in_out.items():
            row = [node_name] + [performance[attr] for attr in attributes]
            data.append(row)

        df = pd.DataFrame(data, columns=["node_name"] + attributes)

        # CSVファイルにエクスポート
        df.to_csv(file_path, index=False)
        print(f"Business performance data exported to {file_path}")


#@250218
# ******************







    #def show_3d_overview(self):
    #    pass

    def show_3d_overview(self):
        # CSVファイルを読み込む
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return  # ユーザーがキャンセルした場合

        # CSVファイルを読み込む
        df = pd.read_csv(file_path)

        # TreeViewを作成してノードを選択させる
        tree_window = tk.Toplevel(self.root)
        tree_window.title("Select Node")
        tree = ttk.Treeview(tree_window)
        tree.pack(fill=tk.BOTH, expand=True)

        # ユニークなノード名のリストを抽出
        node_list = df[['tier', 'node_name', 'parent']].drop_duplicates().sort_values(by='tier')

        # ルートノードを追加
        root_node = tree.insert('', 'end', text='root', iid='root')
        node_id_map = {"root": root_node}

        # ノードをツリー構造に追加
        def add_node(parent, tier, node_name, node_id):
            tree.insert(parent, 'end', node_id, text=f"Tier {tier}: {node_name}")

        for _, row in node_list.iterrows():
            node_id = f"{row['tier']}_{row['node_name']}"
            parent_node_name = row.get("parent", "root")
            if parent_node_name in node_id_map:
                parent = node_id_map[parent_node_name]
                add_node(parent, row["tier"], row["node_name"], node_id)
                node_id_map[row["node_name"]] = node_id
            else:
                # 親ノードが見つからない場合はルートノードを使用
                add_node(root_node, row["tier"], row["node_name"], node_id)
                node_id_map[row["node_name"]] = node_id

        # 選択ボタンの設定
        def select_node():
            selected_item = tree.selection()
            if selected_item:
                node_name = tree.item(selected_item[0], "text").split(": ")[1]
                tree_window.destroy()
                self.plot_3d_graph(df, node_name)

        select_button = tk.Button(tree_window, text="Select", command=select_node)
        select_button.pack()





    def plot_3d_graph(self, df, node_name):
        psi_attr_map = {0: "lightblue", 1: "darkblue", 2: "brown", 3: "gold"}

        x = []
        y = []
        z = []
        labels = []
        colors = []
        week_no_dict = {}
        max_z_value_lot_id_map = {}

        lot_position_map = {}

        for _, row in df.iterrows():
            if row["node_name"] == node_name and pd.notna(row["lot_id"]):
                x_value = row["PSI_attribute"]
                year = row['year']
                week_no = row['week_no']

                # Calculate week_no_serial
                start_year = df['year'].min()
                week_no_serial = (year - start_year) * 53 + week_no
                week_no_dict[week_no_serial] = f"{year}{str(week_no).zfill(2)}"

                y_value = week_no_serial
                lot_id = row['lot_id']

                if (x_value, y_value) not in lot_position_map:
                    lot_position_map[(x_value, y_value)] = 0

                z_value = lot_position_map[(x_value, y_value)] + 1
                lot_position_map[(x_value, y_value)] = z_value

                # Update max z_value for the corresponding (x_value, y_value)
                if (x_value, y_value) not in max_z_value_lot_id_map or z_value > max_z_value_lot_id_map[(x_value, y_value)][0]:
                    max_z_value_lot_id_map[(x_value, y_value)] = (z_value, lot_id)

                x.append(x_value)
                y.append(y_value)
                z.append(z_value)
                labels.append(lot_id)
                colors.append(psi_attr_map[row["PSI_attribute"]])

        # Tkinterのウィンドウを作成
        plot_window = tk.Toplevel(self.root)
        plot_window.title(f"3D Plot for {node_name}")

        # Figureを作成
        fig = plt.figure(figsize=(16, 12))  # 図のサイズを指定
        ax = fig.add_subplot(111, projection='3d')

        # 3Dプロットの作成
        scatter = ax.scatter(x, y, z, c=colors, s=1, depthshade=True)  # s=1でプロットサイズを小さく設定
        ax.set_xlabel('PSI Attribute')
        ax.set_ylabel('Time (YYYYWW)')
        ax.set_zlabel('Lot ID Position')

        # x軸のラベル設定
        ax.set_xticks(list(psi_attr_map.keys()))
        ax.set_xticklabels(["Sales", "CarryOver", "Inventory", "Purchase"], rotation=45, ha='right')

        # y軸のラベル設定
        y_ticks = [week_no_serial for week_no_serial in week_no_dict.keys() if week_no_serial % 2 != 0]
        y_labels = [week_no_dict[week_no_serial] for week_no_serial in y_ticks]
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels, rotation=45, ha='right', fontsize=6)  # フォントサイズをさらに小さく設定

        # 各座標に対応するlot_idの表示（z軸の最大値のみ）
        for (x_value, y_value), (z_value, lot_id) in max_z_value_lot_id_map.items():
            ax.text(x_value, y_value, z_value, lot_id, fontsize=4, color='black', ha='center', va='center')

        # FigureをTkinterのCanvasに追加
        canvas = FigureCanvasTkAgg(fig, master=plot_window)
        canvas.draw()
        canvas.get_tk_widget().pack()

        # Tkinterのメインループを開始
        plot_window.mainloop()

        # プロットをPNGとして保存
        plt.savefig("interactive_plot.png")
        print("Interactive plot saved as interactive_plot.png")





    # PSI and Price for Cash Flow 出力関数
    def psi_price4cf(self):
        print("psi_price4cf")

        # 出力ファイルの保存パス設定
        save_path = os.path.join(self.load_directory, "PSI_PRICE_4_CashFlow.csv")
        print("Save to", save_path)

        # 出力期間の計算
        output_period_outbound = 53 * self.root_node_outbound.plan_range

        # データの収集
        data = []

        def collect_data(node, output_period):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                if attr == 0:
                    price = node.cs_price_sales_shipped
                elif attr == 1:
                    price = node.cs_purchase_total_cost
                elif attr == 2:
                    price = node.cs_purchase_total_cost
                elif attr == 3:
                    price = node.cs_direct_materials_costs
                else:
                    price = 0  # 予期しない値の場合

                row = [node.name, price, attr]
                for week_no in range(output_period):
                    count = len(node.psi4supply[week_no][attr])
                    row.append(count)
                data.append(row)
            
            for child in node.children:
                collect_data(child, output_period)

        # ヘッダーの設定
        headers_outbound = ["node_name", "Price", "PSI_attribute"] + [f"w{i+1}" for i in range(output_period_outbound)]
        
        # root_node_outbound のツリー構造を走査してデータを収集
        collect_data(self.root_node_outbound, output_period_outbound)
        
        # DataFrame を作成して CSV に保存
        df_outbound = pd.DataFrame(data, columns=headers_outbound)
        df_outbound.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"PSI and Price for CashFlow data has been exported to {save_path}")





    def psi_price4cf_OLD(self):
        print("psi_price4cf")

        ## ファイル保存ダイアログを表示して保存先ファイルパスを取得
        #save_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        #if not save_path:
        #    return  # ユーザーがキャンセルした場合

        save_path = os.path.join(self.load_directory, "PSI_PRICE_4_CashFlow.csv")
        print("save to ", save_path)


        # planの出力期間をcalculation
        output_period_outbound = 53 * self.root_node_outbound.plan_range

        # dataの収集
        data = []

        def collect_data(node, output_period):
            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                row = [node.name, attr]
                for week_no in range(output_period):
                    count = len(node.psi4supply[week_no][attr])
                    row.append(count)
                data.append(row)
            for child in node.children:
                collect_data(child, output_period)

        # root_node_outboundのtree構造を走査してdataを収集
        headers_outbound = ["node_name", "PSI_attribute"] + [f"w{i+1}" for i in range(output_period_outbound)]
        collect_data(self.root_node_outbound, output_period_outbound)

        # dataフレームを作成してCSVファイルに保存
        df_outbound = pd.DataFrame(data[:len(data)], columns=headers_outbound)  
        # STOP
        # # 複数のdataフレームを1つにaggregateする場合
        # df_combined = pd.concat([df_outbound, df_inbound])

        df_outbound.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"PSI and Price for CashFlow data has been exported to {save_path}")




    #9. Ensure Data Accuracy
    #Before displaying the chart:
    #
    #Verify that eval_cs_price_sales_shipped and eval_cs_profit are up-to-date.
    #If necessary, call a method like update_evaluation_results() to refresh the data prior to collection.
    
    #For example:
    #    self.update_evaluation_results()  # Ensure data is current
    #    performance_data = self.collect_performance_data()
    
    # This recursive function:
    # Traverses the supply chain tree starting from the root node (root_node_outbound).
    # Stores each node’s revenue and profit in a dictionary, keyed by node name.
    
    def collect_performance_data(self):
        performance_data = {}
        def traverse(node):
            performance_data[node.name] = {
                'revenue': node.eval_cs_price_sales_shipped,
                'profit': node.eval_cs_profit
            }
            for child in node.children:
                traverse(child)
        traverse(self.root_node_outbound)
        return performance_data
    
    # Extracts node names, revenues, and profits from the collected data.
    # Plots two bars per node (revenue in blue, profit in green).
    # Adds labels, a title, and a legend for clarity.
    



    #import matplotlib.pyplot as plt
    #import tkinter as tk
    #from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


    def show_revenue_profit(self):
        # Collect data
        performance_data = self.collect_performance_data()
        nodes = list(performance_data.keys())
        revenues = [data['revenue'] for data in performance_data.values()]
        profits = [data['profit'] for data in performance_data.values()]
        total_costs = [revenue - profit for revenue, profit in zip(revenues, profits)]
        profit_ratios = [round((profit / revenue) * 100, 2) if revenue != 0 else 0 for profit, revenue in zip(profits, revenues)]

        # Create bar chart
        fig, ax = plt.subplots(figsize=(6, 9))  # グラフサイズ調整

        bar_width = 0.35
        index = range(len(nodes))

        # Plot stacked bars
        bars1 = ax.bar(index, total_costs, bar_width, label='Total Cost', color='red', alpha=0.8)
        bars2 = ax.bar(index, profits, bar_width, bottom=total_costs, label='Profit', color='green', alpha=0.8)

        # Add value labels on top of bars (adjusting position)
        for idx, (bar1, bar2) in enumerate(zip(bars1, bars2)):
            height = bar1.get_height() + bar2.get_height()
            formatted_revenue = f'{int(round(revenues[idx])):,}'
            formatted_profit_ratio = f'{profit_ratios[idx]:.2f}%'

            # **数値ラベルの配置調整**
            ax.text(bar1.get_x() + bar1.get_width() / 2.0, 
                    height + 300,  # 上にずらす
                    formatted_revenue, ha='center', va='bottom', fontsize=6, color='black')

            ax.text(bar1.get_x() + bar1.get_width() / 2.0, 
                    height + bar2.get_height() / 2 + 600,  # さらに上にずらす
                    formatted_profit_ratio, ha='center', va='bottom', fontsize=6, color='black')

        # Customize chart
        ax.set_xlabel('Supply Chain Nodes', fontsize=8)
        ax.set_ylabel('Amount', fontsize=8)
        ax.set_title('Revenue and Profit Ratio by Node', fontsize=10)
        ax.set_xticks([i for i in index])
        ax.set_xticklabels(nodes, rotation=90, ha='right', fontsize=6)
        ax.legend(fontsize=8)

        # Reduce chart margins
        fig.tight_layout()

        # Display in GUI
        self.display_chart(fig)


    def show_revenue_profit_OLD(self):
        # Collect data
        performance_data = self.collect_performance_data()
        nodes = list(performance_data.keys())
        revenues = [data['revenue'] for data in performance_data.values()]
        profits = [data['profit'] for data in performance_data.values()]
        total_costs = [revenue - profit for revenue, profit in zip(revenues, profits)]
        profit_ratios = [round((profit / revenue) * 100, 2) if revenue != 0 else 0 for profit, revenue in zip(profits, revenues)]

        # Create bar chart
        #fig, ax = plt.subplots(figsize=(10, 6))
        fig, ax = plt.subplots(figsize=(5, 9))

        bar_width = 0.35
        index = range(len(nodes))

        # Plot stacked bars
        bars1 = ax.bar(index, total_costs, bar_width, label='Total Cost', color='red')
        bars2 = ax.bar(index, profits, bar_width, bottom=total_costs, label='Profit', color='green')

        # Add value labels on top of bars
        for idx, (bar1, bar2) in enumerate(zip(bars1, bars2)):
            height = bar1.get_height() + bar2.get_height()
            formatted_revenue = f'{int(round(revenues[idx])):,}'
            formatted_profit_ratio = f'{profit_ratios[idx]:.2f}%'
            ax.text(bar1.get_x() + bar1.get_width() / 2.0, height, formatted_revenue, ha='center', va='bottom', fontsize=10)  #@250702 fantsize 8=>10
            ax.text(bar1.get_x() + bar1.get_width() / 2.0, height + bar2.get_height() / 2, formatted_profit_ratio, ha='center', va='bottom', fontsize=10)

        # Customize chart
        ax.set_xlabel('Supply Chain Nodes')
        ax.set_ylabel('Amount')
        ax.set_title('Revenue and Profit Ratio by Node')
        ax.set_xticks([i for i in index])
        ax.set_xticklabels(nodes, rotation=90, ha='right')
        ax.legend()

        # Reduce chart margins
        fig.tight_layout()

        # Display in GUI
        self.display_chart(fig)

    def display_chart(self, fig):
        # Clear previous content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Embed chart
        canvas = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)



    #import matplotlib.pyplot as plt
    #import tkinter as tk
    #from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    def show_revenue_profit_OLD(self):
        # Collect data
        performance_data = self.collect_performance_data()
        nodes = list(performance_data.keys())
        revenues = [data['revenue'] for data in performance_data.values()]
        profits = [data['profit'] for data in performance_data.values()]
        total_costs = [revenue - profit for revenue, profit in zip(revenues, profits)]
        profit_ratios = [round((profit / revenue) * 100, 2) if revenue != 0 else 0 for profit, revenue in zip(profits, revenues)]

        # Create bar chart
        fig, ax = plt.subplots(figsize=(5, 9))

        bar_width = 0.35
        index = range(len(nodes))

        # Plot stacked bars
        bars1 = ax.bar(index, total_costs, bar_width, label='Total Cost', color='red')
        bars2 = ax.bar(index, profits, bar_width, bottom=total_costs, label='Profit', color='green')

        # Add value labels on top of bars
        for idx, (bar1, bar2) in enumerate(zip(bars1, bars2)):
            height = bar1.get_height() + bar2.get_height()
            formatted_revenue = f'{int(round(revenues[idx])):,}'
            formatted_profit_ratio = f'{profit_ratios[idx]:.2f}%'
            ax.text(bar1.get_x() + bar1.get_width() / 2.0, height, formatted_revenue, ha='center', va='bottom')
            ax.text(bar1.get_x() + bar1.get_width() / 2.0, height + bar2.get_height() / 2, formatted_profit_ratio, ha='center', va='bottom')

        # Customize chart
        ax.set_xlabel('Supply Chain Nodes')
        ax.set_ylabel('Amount')
        ax.set_title('Revenue and Profit Ratio by Node')
        ax.set_xticks([i for i in index])
        ax.set_xticklabels(nodes, rotation=90, ha='right')
        ax.legend()

        # Display in GUI
        self.display_chart(fig)

    def display_chart_OLD(self, fig):
        # Clear previous content
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        # Embed chart
        canvas = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)







    def cashflow_out_in_net(self):
        print("cashflow_out_in_net")

        # CSVファイルの保存パスを固定
        cashflow_save_path = os.path.join(self.load_directory, "CashFlow_AR_AP_shift.csv")
        profile_outbound_path = os.path.join(self.load_directory, "profile_tree_outbound.csv")


        print("Save to", cashflow_save_path)

        # 出力期間の計算
        output_period_outbound = 53 * self.root_node_outbound.plan_range

        # データの収集
        data = []

        def collect_data(node, output_period, level, position):
            ar_days = node.AR_lead_time  # 売掛金回収期間（例: 30日）
            ap_days = node.AP_lead_time  # 買掛金支払期間（例: 45日）

            ar_shift = int(ar_days // 7)
            ap_shift = int(ap_days // 7)

            weekly_values_cash_in = []
            weekly_values_cash_out = []

            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                if attr == 0:
                    price = node.cs_price_sales_shipped
                elif attr in [1, 2]:
                    price = node.cs_purchase_total_cost
                elif attr == 3:
                    price = node.cs_direct_materials_costs
                else:
                    price = 0  

                row = [node.name, level, position, price, attr]
                weekly_values = [len(node.psi4supply[week_no][attr]) * price for week_no in range(output_period)]

                row.extend(weekly_values)
                data.append(row)

                if attr == 0:  
                    weekly_values_cash_in = np.roll(weekly_values, ar_shift)
                    row = [node.name, level, position, price, "IN"]
                elif attr == 3:  
                    weekly_values_cash_out = np.roll(weekly_values, ap_shift)
                    row = [node.name, level, position, price, "OUT"]
                else:
                    continue 

                row.extend(weekly_values)
                data.append(row)

            # Net Cashの計算
            row = [node.name, level, position, price, "NET"]
            max_length = output_period  

            if len(weekly_values_cash_in) == 0:
                weekly_values_cash_in = np.zeros(max_length)
            if len(weekly_values_cash_out) == 0:
                weekly_values_cash_out = np.zeros(max_length)

            weekly_values_cash_net = np.array(weekly_values_cash_in) - np.array(weekly_values_cash_out)
            row.extend(weekly_values_cash_net)
            data.append(row)

            for i, child in enumerate(node.children):
                collect_data(child, output_period, level + 1, i + 1)

        # CSVヘッダーの設定
        headers_outbound = ["node_name", "Level", "Position", "Price", "PSI_attribute"] + [f"w{i+1}" for i in range(output_period_outbound)]

        # データ収集
        collect_data(self.root_node_outbound, output_period_outbound, 0, 1)

        # DataFrame作成 & CSV保存
        df_outbound = pd.DataFrame(data, columns=headers_outbound)
        df_outbound.to_csv(cashflow_save_path, index=False)



        # CSVデータを別ウィンドウで表示
        self.plot_cash_flow_window(cashflow_save_path, profile_outbound_path)



    # Function to plot cash flow graph with spacing adjustment
    def plot_cash_flow(self, node_data, parent_frame):
        node_name = node_data['node_name'].iloc[0]
        pivot_data = node_data.pivot(index='Week', columns='PSI_attribute', values='Cash Flow').fillna(0)
        pivot_data = pivot_data.rename(columns={'IN': 'Cash In', 'OUT': 'Cash Out', 'NET': 'Net Cash Flow'})

        for col in ['Cash In', 'Cash Out', 'Net Cash Flow']:
            if col not in pivot_data.columns:
                pivot_data[col] = 0

        fig, ax1 = plt.subplots(figsize=(2.3, 1.2), dpi=100)  # Smaller width and height
        fig.subplots_adjust(wspace=0.3, hspace=0.3)  # Adjust space between subplots
        bar_width = 0.2
        ax1.bar(pivot_data.index - bar_width/2, pivot_data["Cash In"], width=bar_width, label="Cash In", color='#d3d3d3', alpha=0.7)
        ax1.bar(pivot_data.index + bar_width/2, pivot_data["Cash Out"], width=bar_width, label="Cash Out", color='#ff69b4', alpha=0.7)

        ax2 = ax1.twinx()
        ax2.plot(pivot_data.index, pivot_data["Net Cash Flow"], label="Net Cash Flow", marker='o', linestyle='-', color='#1f77b4', linewidth=1, markersize=2)

        # Smaller font size for better fitting
        ax1.set_xlabel("Weeks", fontsize=10) #@250702 fantsize 6=>10
        ax1.set_ylabel("Cash In / Cash Out", fontsize=10)
        ax2.set_ylabel("Net Cash Flow", fontsize=10)
        ax1.legend(loc='upper left', fontsize=10) #@250702 fantsize 5=>10
        ax2.legend(loc='upper right', fontsize=10)

        # Change tick label font sizes
        ax1.tick_params(axis='x', labelsize=4)
        ax1.tick_params(axis='y', labelsize=4)
        ax2.tick_params(axis='y', labelsize=4)

        fig.suptitle(f'Cash Flow for {node_name}', fontsize=10) #@250702 fantsize 7=>10

        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, padx=2, pady=2)

        plt.close(fig)  # Close figure to free memory




    def traverse_and_plot(self, data, tree_structure, root_node_name, scrollable_frame, parent_col):
        node_queue = [(root_node_name, 0)]  # Queue for BFS traversal (node_name, level)
        row_counter = 0  # Start at row 0
        root_node_processed = False

        while node_queue:
            current_node_name, current_level = node_queue.pop(0)
            children = tree_structure[tree_structure[parent_col] == current_node_name]

            if not root_node_processed:
                for _, child in children.iterrows():
                    child_node_name = child['Child_node']
                    node_queue.append((child_node_name, current_level + 1))
                root_node_processed = True
                continue

            if len(children) > 0:
                node_data = data[data['node_name'] == current_node_name]

                row_frame = tk.Frame(scrollable_frame)
                row_frame.grid(row=row_counter, column=0, sticky="w", padx=5, pady=5)

                if not node_data.empty and current_level > 0:
                    parent_frame = tk.Frame(row_frame)
                    parent_frame.pack(side=tk.LEFT, padx=5, pady=5)
                    self.plot_cash_flow(node_data, parent_frame)

                for _, child in children.iterrows():
                    child_node_name = child['Child_node']
                    node_queue.append((child_node_name, current_level + 1))

                    child_data = data[data['node_name'] == child_node_name]
                    if not child_data.empty:
                        child_frame = tk.Frame(row_frame)
                        child_frame.pack(side=tk.LEFT, padx=5, pady=5)
                        self.plot_cash_flow(child_data, child_frame)

                row_counter += 1



    def traverse_and_plot_preorder(self, data, tree_structure, root_node_name, scrollable_frame, parent_col):
        node_stack = [(root_node_name, 0)]  # Stack for Preorder traversal (node_name, level)
        row_counter = 0  # Start at row 0

        while node_stack:
            current_node_name, current_level = node_stack.pop()
            children = tree_structure[tree_structure[parent_col] == current_node_name]

            node_data = data[data['node_name'] == current_node_name]

            row_frame = tk.Frame(scrollable_frame)
            row_frame.grid(row=row_counter, column=0, sticky="w", padx=5, pady=5)

            if not node_data.empty:
                parent_frame = tk.Frame(row_frame)
                parent_frame.pack(side=tk.LEFT, padx=5, pady=5)
                self.plot_cash_flow(node_data, parent_frame)

            for _, child in children.iterrows():
                child_node_name = child['Child_node']
                node_stack.append((child_node_name, current_level + 1))

            row_counter += 1




    def plot_cash_flow_window(self, cashflow_save_path, profile_outbound_path):

        df = pd.read_csv(cashflow_save_path)
        df = df.drop(columns=['Price'])  
        df_melted = df.melt(id_vars=['node_name', 'Level', 'Position', 'PSI_attribute'], var_name='Week', value_name='Cash Flow')
        df_melted['Week'] = df_melted['Week'].str.extract(r'(\d+)').astype(int)
        cash_flow_data = df_melted.groupby(['node_name', 'Level', 'Position', 'PSI_attribute', 'Week'])['Cash Flow'].sum().reset_index()








        cash_window = tk.Toplevel(self.root)
        cash_window.title("Cash Flow Analyzer")
        cash_window.geometry("1400x800")

        frame = ttk.Frame(cash_window)
        frame.pack(pady=10)

        canvas = tk.Canvas(cash_window)

        #scrollable_frame = ttk.Frame(canvas)
        #canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        #canvas.pack(fill=tk.BOTH, expand=True)

        v_scrollbar = tk.Scrollbar(cash_window, orient="vertical", command=canvas.yview)
        h_scrollbar = tk.Scrollbar(cash_window, orient="horizontal", command=canvas.xview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=X)














        # Load tree structure from CSV file
        def load_tree_structure(file_path):
            df = pd.read_csv(file_path)
            print("CSV Columns:", df.columns.tolist())  # Debugging: Print columns to identify correct names
            return df


        ## Load tree structure from CSV file
        #def load_tree_structure(file_path="profile_tree_outbound.csv"):
        #    df = pd.read_csv(file_path)
        #    print("CSV Columns:", df.columns.tolist())  # Debugging: Print columns to identify correct names
        #    return df


        # Identify parent column dynamically
        def get_parent_column(tree_structure):
            possible_names = ["Parent_node", "Parent_no", "Parent", "ParentNode"]
            for col in possible_names:
                if col in tree_structure.columns:
                    print("Detected Parent Column:", col)  # Debugging: Confirm detected column
                    return col
            raise KeyError("Parent column not found in tree structure CSV.")




        #tree_structure = load_tree_structure()
        tree_structure = load_tree_structure(profile_outbound_path)

        parent_col = get_parent_column(tree_structure)

        print("parent_col", parent_col)



        # Load and process CSV file for cash flow data
        def load_and_process_csv(file_path):
            df = pd.read_csv(file_path)
            cash_flow_data = df.drop(columns=['Price'])
            cash_flow_long = cash_flow_data.melt(id_vars=['node_name', 'Level', 'Position', 'PSI_attribute'], var_name='Week', value_name='Cash Flow')
            cash_flow_long['Week'] = cash_flow_long['Week'].str.extract(r'(\d+)').astype(int)
            return cash_flow_long.groupby(['node_name', 'Level', 'Position', 'PSI_attribute', 'Week'])['Cash Flow'].sum().reset_index()


        cash_flow_agg = load_and_process_csv(cashflow_save_path)

        unique_nodes = tree_structure[parent_col].unique()
        root_node = unique_nodes[0] if len(unique_nodes) > 0 else None

        print("root_node", root_node)




            #if root_node:
        self.traverse_and_plot(cash_flow_agg, tree_structure, root_node, scrollable_frame, parent_col)


        #self.traverse_and_plot_preorder(cash_flow_data, tree_structure, tree_structure[parent_col].iloc[0], scrollable_frame, parent_col)



    def plot_cash_flow(self, node_data, parent_frame):
        node_name = node_data['node_name'].iloc[0]
        pivot_data = node_data.pivot(index='Week', columns='PSI_attribute', values='Cash Flow').fillna(0)
        pivot_data = pivot_data.rename(columns={'IN': 'Cash In', 'OUT': 'Cash Out', 'NET': 'Net Cash Flow'})

        for col in ['Cash In', 'Cash Out', 'Net Cash Flow']:
            if col not in pivot_data.columns:
                pivot_data[col] = 0

        fig, ax1 = plt.subplots(figsize=(3, 1.5), dpi=100)
        fig.subplots_adjust(wspace=0.2)
        bar_width = 0.2

        ax1.bar(pivot_data.index - bar_width / 2, pivot_data["Cash In"], width=bar_width, label="Cash In", color='#d3d3d3', alpha=0.7)
        ax1.bar(pivot_data.index + bar_width / 2, pivot_data["Cash Out"], width=bar_width, label="Cash Out", color='#ff69b4', alpha=0.7)

        ax2 = ax1.twinx()
        ax2.plot(pivot_data.index, pivot_data["Net Cash Flow"], label="Net Cash Flow", marker='o', linestyle='-', color='#1f77b4', linewidth=1, markersize=2)

        ax1.set_xlabel("Weeks", fontsize=10) #@250702 fantsize 6=>10
        ax1.set_ylabel("Cash In / Cash Out", fontsize=10)
        ax2.set_ylabel("Net Cash Flow", fontsize=10)
        ax1.legend(loc='upper left', fontsize=10) #@250702 fantsize 5=>10
        ax2.legend(loc='upper right', fontsize=10)
        ax1.tick_params(axis='x', labelsize=8)
        ax1.tick_params(axis='y', labelsize=8)
        ax2.tick_params(axis='y', labelsize=8)
        fig.suptitle(f'Cash Flow for {node_name}', fontsize=10) #@250702 fantsize 7=>10

        canvas = FigureCanvasTkAgg(fig, master=parent_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        plt.close(fig)




    def cashflow_out_in_net_OLD2(self):
        print("cashflow_out_in_net")

        ## PSI and Price for Cash Flow 出力関数
        #def psi_price4cf_AR_AP_shift(self):
        # 出力ファイルの保存パス設定
        save_path = os.path.join(self.load_directory, "CashFlow_AR_AP_shift.csv")
        print("Save to", save_path)

        # 出力期間の計算
        output_period_outbound = 53 * self.root_node_outbound.plan_range

        # データの収集
        data = []

        def collect_data(node, output_period, level, position):
            # AP/ARリードタイム（日）
            ar_days = node.AR_lead_time  # 売掛金回収期間（例: 30日）
            ap_days = node.AP_lead_time  # 買掛金支払期間（例: 45日）

            # 週単位に変換
            ar_shift = int(ar_days // 7)
            ap_shift = int(ap_days // 7)

            weekly_values_cash_in = []
            weekly_values_cash_out = []

            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                if attr == 0:
                    price = node.cs_price_sales_shipped
                elif attr == 1:
                    price = node.cs_purchase_total_cost
                elif attr == 2:
                    price = node.cs_purchase_total_cost
                elif attr == 3:
                    price = node.cs_direct_materials_costs
                else:
                    price = 0  # 予期しない値の場合

                # **** BEFORE CASH OFFSET
                row = [node.name, level, position, price, attr]
                weekly_values = []

                for week_no in range(output_period):
                    count = len(node.psi4supply[week_no][attr])
                    weekly_values.append(count * price)

                # @ BEFORE
                row.extend(weekly_values)
                data.append(row)
                # ****

                # @ CHANGE header STOP values
                ## **** AFTER CASH OFFSET
                if attr == 0:  # 売上（Cash In）
                    weekly_values = np.roll(weekly_values, ar_shift)
                    weekly_values_cash_in = weekly_values.copy()
                    row = [node.name, level, position, price, "IN"]
                elif attr == 3:  # 仕入れ（Cash Out）
                    weekly_values = np.roll(weekly_values, ap_shift)
                    weekly_values_cash_out = weekly_values.copy()
                    row = [node.name, level, position, price, "OUT"]
                else:
                    row = [node.name, level, position, price, attr]  # reset header

                # @ STOP
                row.extend(weekly_values)
                print("row", len(row), row)

                data.append(row)

            # **** NET CASH
            row = [node.name, level, position, price, "NET"]  # attr=40 net_cash
            weekly_values = []

            # 長さを統一して np.array に変換（ゼロ埋め対応）
            max_length = output_period  # 週数

            if len(weekly_values_cash_in) == 0:
                weekly_values_cash_in = np.zeros(max_length)
            if len(weekly_values_cash_out) == 0:
                weekly_values_cash_out = np.zeros(max_length)

            # @ cach net
            weekly_values_cash_net = []

            # NumPy配列に変換して要素ごとに計算
            weekly_values_cash_net = np.array(weekly_values_cash_in) - np.array(weekly_values_cash_out)

            row.extend(weekly_values_cash_net)
            data.append(row)

            for i, child in enumerate(node.children):
                collect_data(child, output_period, level + 1, i + 1)

        # ヘッダーの設定
        headers_outbound = ["node_name", "Level", "Position", "Price", "PSI_attribute"] + [f"w{i+1}" for i in range(output_period_outbound)]

        # root_node_outbound のツリー構造を走査してデータを収集
        collect_data(self.root_node_outbound, output_period_outbound, 0, 1)

        # DataFrame を作成して CSV に保存
        df_outbound = pd.DataFrame(data, columns=headers_outbound)
        df_outbound.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"PSI and Price for CashFlow data has been exported to {save_path}")







    def cashflow_out_in_net_OLD(self):
        print("cashflow_out_in_net")

    ## PSI and Price for Cash Flow 出力関数
    #def psi_price4cf_AR_AP_shift(self):

        # 出力ファイルの保存パス設定
        save_path = os.path.join(self.load_directory, "CashFlow_AR_AP_shift.csv")

        print("Save to", save_path)

        # 出力期間の計算
        output_period_outbound = 53 * self.root_node_outbound.plan_range



        # データの収集
        data = []

        def collect_data(node, output_period):



            # AP/ARリードタイム（日）
            ar_days = node.AR_lead_time  # 売掛金回収期間（例: 30日）
            ap_days = node.AP_lead_time  # 買掛金支払期間（例: 45日）
            
            # 週単位に変換
            ar_shift = int( ar_days // 7 )
            ap_shift = int( ap_days // 7 )


            weekly_values_cash_in  = []
            weekly_values_cash_out = []


            for attr in range(4):  # 0:"Sales", 1:"CarryOver", 2:"Inventory", 3:"Purchase"
                if attr == 0:
                    price = node.cs_price_sales_shipped
                elif attr == 1:
                    price = node.cs_purchase_total_cost
                elif attr == 2:
                    price = node.cs_purchase_total_cost
                elif attr == 3:
                    price = node.cs_direct_materials_costs
                else:
                    price = 0  # 予期しない値の場合



                # **** BEFORE CASH OFFSET
                row = [node.name, price, attr]
                weekly_values          = []

                for week_no in range(output_period):
                    count = len(node.psi4supply[week_no][attr])
                    weekly_values.append(count * price)
                
                #@ BEFORE
                row.extend(weekly_values)
                data.append(row)
                # ****


                #@ CHANGE header STOP values
                ## **** AFTER CASH OFFSET

                #row = [node.name, price, attr]
                #weekly_values          = []

                # キャッシュフローのオフセット処理
                if attr == 0:  # 売上（Cash In）
                    weekly_values = np.roll(weekly_values, ar_shift)
                    weekly_values_cash_in = weekly_values.copy()

                    row = [node.name, price, "IN"]

                elif attr == 3:  # 仕入れ（Cash Out）
                    weekly_values = np.roll(weekly_values, ap_shift)
                    weekly_values_cash_out = weekly_values.copy()

                    row = [node.name, price, "OUT"]

                else:
                    row = [node.name, price, attr] # reset header

                
                
                #@ STOP
                ## キャッシュフローのオフセット処理
                #if attr == 0:  # 売上（Cash In）
                #    weekly_values         = np.roll(weekly_values, ar_shift)
                #    weekly_values_cash_in = weekly_values
                #elif attr == 3:  # 仕入れ（Cash Out）
                #    weekly_values         = np.roll(weekly_values, ap_shift)
                #    weekly_values_cash_out= weekly_values
                


                #@ AFTER
                row.extend(weekly_values)
                print("row", len(row), row)

                data.append(row)





            # **** NET CASH
            row = [node.name, price, "NET" ]  # attr=40 net_cash
            #row = [node.name, price, attr]

            weekly_values          = []

            # 長さを統一して np.array に変換（ゼロ埋め対応）
            max_length = output_period  # 週数

            if len(weekly_values_cash_in) == 0:
                weekly_values_cash_in = np.zeros(max_length)
            if len(weekly_values_cash_out) == 0:
                weekly_values_cash_out = np.zeros(max_length)


            #@ cach net 
            weekly_values_cash_net = []

            # NumPy配列に変換して要素ごとに計算
            weekly_values_cash_net = np.array(weekly_values_cash_in) - np.array(weekly_values_cash_out)

            row.extend(weekly_values_cash_net)
            data.append(row)


            
            for child in node.children:
                collect_data(child, output_period)


        # ヘッダーの設定
        headers_outbound = ["node_name", "Price", "PSI_attribute"] + [f"w{i+1}" for i in range(output_period_outbound)]
        
        # root_node_outbound のツリー構造を走査してデータを収集
        collect_data(self.root_node_outbound, output_period_outbound)
        
        # DataFrame を作成して CSV に保存

        df_outbound = pd.DataFrame(data, columns=headers_outbound)
        df_outbound.to_csv(save_path, index=False)

        # 完了メッセージを表示
        messagebox.showinfo("CSV Export", f"PSI and Price for CashFlow data has been exported to {save_path}")





    
    
    # ******************************
    # define planning ENGINE
    # ******************************

    #def demand_planning(self):
    #    pass

    def demand_planning(self):
        # Implement forward planning logic here
        print("Forward planning executed.")

        #@240903@241106
        calc_all_psi2i4demand(self.root_node_outbound)


        self.update_evaluation_results()

        #@241212 add
        self.decouple_node_selected = []
        self.view_nx_matlib()

        self.root.after(1000, self.show_psi("outbound", "demand"))
        #self.root.after(1000, self.show_psi_graph)
        #self.show_psi_graph() # this event do not live 






    #def demand_leveling(self):
    #    pass

    #@250120 STOP with "name chaged"
    def demand_leveling(self):
        # Demand Leveling logic here
        print("Demand Leveling executed.")


        # *********************************
        # Demand LEVELing on shipping yard / with pre_production week
        # *********************************

        year_st  = 2020
        year_end = 2021

        year_st  = self.plan_year_st
        year_end = year_st + self.plan_range - 1

        pre_prod_week = self.pre_proc_LT

        # STOP
        #year_st = df_capa_year["year"].min()
        #year_end = df_capa_year["year"].max()

        # root_node_outboundのsupplyの"S"のみを平準化して生成している
        demand_leveling_on_ship(self.root_node_outbound, pre_prod_week, year_st, year_end)


        # root_node_outboundのsupplyの"PSI"を生成している
        ##@241114 KEY CODE
        self.root_node_outbound.calcS2P_4supply()  #mother plantのconfirm S=> P
        self.root_node_outbound.calcPS2I4supply()  #mother plantのPS=>I


        #@241114 KEY CODE
        # ***************************************
        # その3　都度のparent searchを実行 setPS_on_ship2node
        # ***************************************
        feedback_psi_lists(self.root_node_outbound, self.nodes_outbound)


        #feedback_psi_lists(self.root_node_outbound, node_psi_dict_Ot4Sp, self.nodes_outbound)


        # STOP
        #decouple_node_names = [] # initial PUSH with NO decouple node
        ##push_pull_on_decouple
        #push_pull_all_psi2i_decouple4supply5(
        #    self.root_node_outbound,
        #    decouple_node_names )



        #@241114 KEY CODE
        #@240903

        #calc_all_psi2i4demand(self.root_node_outbound)
        #calc_all_psi2i4supply(self.root_node_outbound)


        self.update_evaluation_results()

        # PSI計画の初期状態をバックアップ
        self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')

        self.view_nx_matlib()

        self.root.after(1000, self.show_psi("outbound", "supply"))
        #self.root.after(1000, self.show_psi_graph)




    def psi_backup(self, node, status_name):
        return copy.deepcopy(node)

    def psi_restore(self, node_backup, status_name):
        return copy.deepcopy(node_backup)

    def psi_backup_to_file(self, node, filename):
        with open(filename, 'wb') as file:
            pickle.dump(node, file)

    def psi_restore_from_file(self, filename):
        with open(filename, 'rb') as file:
            node_backup = pickle.load(file)
        return node_backup




    def supply_planning(self):
        # Check if the necessary data is loaded
        if self.root_node_outbound is None or self.nodes_outbound is None:
            print("Error: PSI Plan data is not loaded. Please load the data first.")
            tk.messagebox.showerror("Error", "PSI Plan data is NOT loaded. please File Open parameter directory first.")
            return
    
        # Implement forward planning logic here
        print("Supply planning with Decoupling points")
    
        # Restore PSI data from a backup file
        self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')
    
        if self.decouple_node_selected == []:
            # Search nodes_decouple_all[-2], that is "DAD" nodes
            nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound    )
            print("nodes_decouple_all", nodes_decouple_all)
    
            # [-2] will be "DAD" node, the point of Delivery and Distribution
            decouple_node_names = nodes_decouple_all[-2]
        else:
            decouple_node_names = self.decouple_node_selected
    
        # Perform supply planning logic
        push_pull_all_psi2i_decouple4supply5(
            self.root_node_outbound, decouple_node_names
        )
    
        # Evaluate the results
        self.update_evaluation_results()
    
    
        #@250218 STOP
        ## Cash OUT/IN
        #self.cash_flow_print()
    
    
    
        # Update the network visualization
        self.decouple_node_selected = decouple_node_names
        self.view_nx_matlib4opt()
    
        # Update the PSI area
        self.root.after(1000, self.show_psi("outbound", "supply"))
    
    
    
    
    #def eval_buffer_stock(self):
    #    pass

    def eval_buffer_stock(self):

        # Check if the necessary data is loaded
        if self.root_node_outbound is None or self.nodes_outbound is None:
            print("Error: PSI Plan data is not loaded. Please load the data first.")
            tk.messagebox.showerror("Error", "PSI Plan data is NOT loaded. please File Open parameter directory first.")
            return

        print("eval_buffer_stock with Decoupling points")

        # This backup is in "demand leveling"
        ## PSI計画の初期状態をバックアップ
        #self.psi_backup_to_file(self.root_node_outbound, 'psi_backup.pkl')

        nodes_decouple_all = make_nodes_decouple_all(self.root_node_outbound)
        print("nodes_decouple_all", nodes_decouple_all)

        for i, decouple_node_names in enumerate(nodes_decouple_all):
            print("nodes_decouple_all", nodes_decouple_all)


            # PSI計画の状態をリストア
            self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')

            push_pull_all_psi2i_decouple4supply5(self.root_node_outbound, decouple_node_names)
            self.update_evaluation_results()

            print("decouple_node_names", decouple_node_names)
            print("self.total_revenue", self.total_revenue)
            print("self.total_profit", self.total_profit)

            self.decouple_node_dic[i] = [self.total_revenue, self.total_profit, decouple_node_names]

            ## network area
            #self.view_nx_matlib()

            ##@241207 TEST
            #self.root.after(1000, self.show_psi("outbound", "supply"))


        self.display_decoupling_patterns()
        # PSI area => move to selected_node in window





    def optimize_network(self):

        # Check if the necessary data is loaded
        if self.root_node_outbound is None or self.nodes_outbound is None:
            print("Error: PSI Plan data is not loaded. Please load the data first.")
            tk.messagebox.showerror("Error", "PSI Plan data is NOT loaded. please File Open parameter directory first.")
            return

        print("optimizing start")


    #@ STOP
    #def optimize_and_view_nx_matlib(self):

        G = nx.DiGraph()    # base display field


        Gdm_structure = nx.DiGraph()  # optimise for demand side
        #Gdm = nx.DiGraph()  # optimise for demand side

        Gsp = nx.DiGraph()  # optimise for supply side

        self.G = G
        self.Gdm_structure = Gdm_structure
        self.Gsp = Gsp


        root_node_outbound = self.root_node_outbound 
        nodes_outbound = self.nodes_outbound     
        root_node_inbound = self.root_node_inbound  
        nodes_inbound = self.nodes_inbound      

        pos_E2E, G, Gdm_structure, Gsp = self.show_network_E2E_matplotlib(
        #pos_E2E, Gdm_structure, Gsp = show_network_E2E_matplotlib(
        #pos_E2E, flowDict_dm, flowDict_sp, Gdm_structure, Gsp = show_network_E2E_matplotlib(
            root_node_outbound, nodes_outbound, 
            root_node_inbound, nodes_inbound, 
            G, Gdm_structure, Gsp
        )


        # **************************************************
        # optimizing here
        # **************************************************

        G_opt = Gdm_structure.copy()


        # 最適化パラメータをリセット
        self.reset_optimization_params(G_opt)

        #@241229 ADD
        self.reset_optimized_path(G_opt)

        # 新しい最適化パラメータを設定
        self.set_optimization_params(G_opt)

        flowDict_opt = self.flowDict_opt
        print("optimizing here flowDict_opt", flowDict_opt)


        # 最適化を実行
        # fllowing set should be done here
        #self.flowDict_opt = flowDict_opt
        #self.flowCost_opt = flowCost_opt

        self.run_optimization(G_opt)
        print("1st run_optimization self.flowDict_opt", self.flowDict_opt)







        # flowCost_opt = self.flowCost_opt # direct input

        G_result = G_opt.copy()


        G_view = G_result.copy()
        self.add_optimized_path(G_view, self.flowDict_opt)






        #@241205 STOP **** flowDict_optを使ったGのE2Eの表示系に任せる
        ## 前回の最適化pathをリセット
        self.reset_optimized_path(G_result)
        #
        ## 新しい最適化pathを追加
        G_result = G_opt.copy()
        self.add_optimized_path(G_result, self.flowDict_opt)
        
        # 最適化pathの表示（オプション）
        #print("Iteration", i + 1)
        print("Optimized Path:", self.flowDict_opt)
        print("Optimized Cost:", self.flowCost_opt)


        # make optimized tree and PSI planning and show it
        flowDict_opt = self.flowDict_opt


        optimized_nodes = {} # 初期化
        optimized_nodes = self.create_optimized_tree(flowDict_opt)


        if not optimized_nodes:
            error_message = "error: optimization with NOT enough supply"
            print(error_message)
            self.show_error_message(error_message)  # 画面にエラーメッセージを表示する関数
            return


        print("optimized_nodes", optimized_nodes)
        optimized_root = optimized_nodes['supply_point']
        self.optimized_root = optimized_root



        #@241227 MEMO 
        # 最適化されたnodeの有無でPSI表示をON/OFFしているが、これに加えて
        # ここでは、最適化nodeは存在し、、年間の値が0の時、
        # 年間供給量を月次に按分して供給するなどの処理を追加する



        # *********************************
        # making limited_supply_nodes
        # *********************************
        leaf_nodes_out       = self.leaf_nodes_out  # all leaf_nodes
        optimized_nodes_list = []              # leaf_node on targetted market
        limited_supply_nodes = []              # leaf_node Removed from target

        # 1. optimized_nodes辞書からキー項目をリストoptimized_nodes_listに抽出
        optimized_nodes_list = list(optimized_nodes.keys())

        # 2. leaf_nodes_outからoptimized_nodes_listの要素を排除して
        # limited_supply_nodesを生成
        limited_supply_nodes = [node for node in leaf_nodes_out if node not in optimized_nodes_list]

        # 結果を表示
        print("optimized_nodes_list:", optimized_nodes_list)
        print("limited_supply_nodes:", limited_supply_nodes)


# 最適化の結果をPSIに反映する方法
# 1. 入力ファイルS_month_data.csvをdataframeに読込み
# 2. limited_supply_nodesの各要素node nameに該当するS_month_dataのSの値を
#    すべて0 clearする。
# 3. 結果を"S_month_optimized.csv"として保存する
# 4. S_month_optimized.csvを入力として、load_data_opt_filesからPSI planする



        # limited_supply_nodesのリスト
        #limited_supply_nodes = ['MUC_N', 'MUC_D', 'MUC_I', 'SHA_I', 'NYC_D', 'NYC_I', 'LAX_D', 'LAX_I']












        # 入力CSVファイル名
        input_csv = 'S_month_data.csv'


        # デバッグ用コード追加
        print(f"self.directory: {self.directory}")
        print(f"input_csv: {input_csv}")

        if self.directory is None or input_csv is None:
            raise ValueError("self.directory または input_csv が None になっています。適切な値を設定してください。")


        input_csv_path = os.path.join(self.directory, input_csv)


        # 出力CSVファイル名
        output_csv = 'S_month_optimized.csv'
        output_csv_path = os.path.join(self.directory, output_csv)




        # S_month.csvにoptimized_demandをセットする
        # optimized leaf_node以外を0 clearする


        #@ STOP
        # 最適化にもとづく供給配分 ここでは簡易的にon-offしているのみ
        # 本来であれば、最適化の供給配分を詳細に行うべき所
        #self.clear_s_values(limited_supply_nodes, input_csv_path, output_csv_path)


        input_csv = 'S_month_data.csv'
        output_csv = 'S_month_optimized.csv'

        input_csv_path = os.path.join(self.directory, input_csv)
        output_csv_path = os.path.join(self.directory, output_csv)

        self.clear_s_values(self.flowDict_opt, input_csv_path, output_csv_path)



        ## **************************************
        ## input_csv = 'S_month_optimized.csv' load_files & planning
        ## **************************************
        #
        self.load_data_files4opt()     # loading with 'S_month_optimized.csv'

        #
        self.plan_through_engines4opt()




        # **************************************
        # いままでの評価と描画系
        # **************************************




        # *********************
        # evaluation@241220
        # *********************
        #@241225 memo "root_node_out_opt"のtreeにはcs_xxxxがセットされていない
        self.update_evaluation_results4optimize()


        # *********************
        # network graph
        # *********************
        # STAY ORIGINAL PLAN
        # selfのhandle nameは、root_node_outboundで、root_node_out_optではない
        # 
        # グラフ描画関数を呼び出し  最適ルートを赤線で表示
        #
        # title revenue, profit, profit_ratio
        self.draw_network4opt(G, Gdm_structure, Gsp, pos_E2E, self.flowDict_opt)

        #self.draw_network4opt(G, Gdm, Gsp, pos_E2E, flowDict_dm, flowDict_sp, flowDict_opt)


        # *********************
        # PSI graph
        # *********************
        self.root.after(1000, self.show_psi_graph4opt)
        #self.root.after(1000, self.show_psi_graph)
        
        #@ ADD
        # パラメータの初期化と更新を呼び出し
        self.updated_parameters()
        #@ STOP
        #self.updated_parameters4opt()




    def Inbound_DmBw(self):


        connect_outbound2inbound(self.root_node_outbound, self.root_node_inbound)
    
    
        calc_all_psiS2P2childS_preorder(self.root_node_inbound)


        #@250120 eval and view
        self.update_evaluation_results()

        #@241212 add
        self.decouple_node_selected = []
        self.view_nx_matlib()

        self.root.after(1000, self.show_psi("inbound", "demand"))
        #self.root.after(1000, self.show_psi("outbound", "demand"))




        pass



    def Inbound_SpFw(self):


        #@240907 demand2supply
        # copy demand layer to supply layer # メモリーを消費するので要修正
    
        self.node_psi_dict_In4Sp = psi_dict_copy(
                                 self.node_psi_dict_In4Dm, # in demand  .copy()
                                 self.node_psi_dict_In4Sp   # in supply
                              )
    
        # In4Dmの辞書をself.psi4supply = node_psi_dict_In4Dm[self.name]でre_connect
    
        def re_connect_suppy_dict2psi(node, node_psi_dict):
    
            node.psi4supply = node_psi_dict[node.name]
    
            for child in node.children:
    
                re_connect_suppy_dict2psi(child, node_psi_dict)
    
    
        re_connect_suppy_dict2psi(self.root_node_inbound, self.node_psi_dict_In4Sp)
    
        calc_all_psi2i4supply_post(self.root_node_inbound)
    
    
    
        #@250120 eval and view
        self.update_evaluation_results()

        #@241212 add
        self.decouple_node_selected = []
        self.view_nx_matlib()

        self.root.after(1000, self.show_psi("inbound", "supply"))
        #self.root.after(1000, self.show_psi("outbound", "demand"))





    
        pass



# **** 19 call_backs END*****



# **** Start of SUB_MODULE for Optimization ****

    def _load_tree_structure(self, load_directory):

        with open(f"{load_directory}/root_node_outbound.pkl", 'rb') as f:
            self.root_node_outbound = pickle.load(f)
            print(f"root_node_outbound loaded: {self.root_node_outbound}")

        with open(f"{load_directory}/root_node_inbound.pkl", 'rb') as f:
            self.root_node_inbound = pickle.load(f)
            print(f"root_node_inbound loaded: {self.root_node_inbound}")


        if os.path.exists(f"{load_directory}/root_node_out_opt.pkl"):
            with open(f"{load_directory}/root_node_out_opt.pkl", 'rb') as f:
                self.root_node_out_opt = pickle.load(f)
                print(f"root_node_out_opt loaded: {self.root_node_out_opt}")
        else:
            self.flowDict_opt = {}  # NO optimize
            pass





    def reset_optimization_params(self, G):
        for u, v in G.edges():
            G[u][v]['capacity'] = 0
            G[u][v]['weight'] = 0
        for node in G.nodes():
            G.nodes[node]['demand'] = 0
    
    
    def reset_optimized_path(self, G):
        for u, v in G.edges():
            if 'flow' in G[u][v]:
                del G[u][v]['flow']
    
    
    def run_optimization(self, G):

        #flow_dict = nx.min_cost_flow(G)
        #cost = nx.cost_of_flow(G, flow_dict)
        #return flow_dict, cost


        # ************************************
        # optimize network
        # ************************************
        try:
    
            flowCost_opt, flowDict_opt = nx.network_simplex(G)

        except Exception as e:
            print("Error during optimization:", e)
            return

        self.flowCost_opt = flowCost_opt
        self.flowDict_opt = flowDict_opt

        print("flowDict_opt", flowDict_opt)
        print("flowCost_opt", flowCost_opt)

        print("end optimization")
    
    
    def add_optimized_path(self, G, flow_dict):
        for u in flow_dict:
            for v, flow in flow_dict[u].items():
                if flow > 0:
                    G[u][v]['flow'] = flow
    
    

    # 画面にエラーメッセージを表示する関数
    def show_error_message(self, message):
        error_window = tk.Toplevel(self.root)
        error_window.title("Error")
        tk.Label(error_window, text=message, fg="red").pack()
        tk.Button(error_window, text="OK", command=error_window.destroy).pack()




    # オリジナルノードからコピーする処理
    def copy_node(self, node_name):
        original_node = self.nodes_outbound[node_name]  #オリジナルノードを取得
        copied_node = copy.deepcopy(original_node)  # deepcopyを使ってコピー
        return copied_node




    def create_optimized_tree(self, flowDict_opt):
        # Optimized Treeの生成
        optimized_nodes = {}
        for from_node, flows in flowDict_opt.items():

            if from_node == 'sales_office': # 末端の'sales_office'はtreeの外
                pass
            else:

                for to_node, flow in flows.items():

                    if to_node == 'sales_office': # 末端の'sales_office'はtreeの外
                        pass
                    else:


                        if flow > 0:
                            if from_node not in optimized_nodes:
                                optimized_nodes[from_node] = self.copy_node(from_node)
                            if to_node not in optimized_nodes:
                                optimized_nodes[to_node] = self.copy_node(to_node)
                                optimized_nodes[to_node].parent =optimized_nodes[from_node]
        return optimized_nodes




    def set_optimization_params(self, G):
        print("optimization start")

        #Gdm = self.Gdm

        nodes_outbound = self.nodes_outbound
        root_node_outbound = self.root_node_outbound

        print("root_node_outbound.name", root_node_outbound.name)

        # Total Supply Planの取得
        total_supply_plan = int( self.total_supply_plan )

        #total_supply_plan = int(self.tsp_entry.get())


        print("setting capacity")
        max_capacity = 1000000  # 設定可能な最大キャパシティ（適切な値を設定）
        scale_factor_capacity = 1  # キャパシティをスケールするための因子
        scale_factor_demand   = 1  # スケーリング因子

        for edge in G.edges():
            from_node, to_node = edge

            # if node is leaf_node

            #@250103 STOP
            #if from_node in self.leaf_nodes_out and to_node == 'sales_office':

            #@250103 RUN
            if to_node in self.leaf_nodes_out:


                #@250103 RUN
                # ********************************************
                # scale_factor_capacity
                #@241220 TAX100... demand curve... Price_Up and Demand_Down
                # ********************************************
                capacity = int(nodes_outbound[to_node].nx_capacity * scale_factor_capacity)

                #@ STOP
                ## ********************************************
                ## scale_factor_capacity
                ##@241220 TAX100... demand curve... Price_Up and Demand_Down
                ## ********************************************
                #capacity = int(nodes_outbound[from_node].lot_counts_all * scale_factor_capacity)


                G.edges[edge]['capacity'] = capacity
            else:
                G.edges[edge]['capacity'] = max_capacity  # 最大キャパシティを設定
            print("G.edges[edge]['capacity']", edge, G.edges[edge]['capacity'])


        #@250102 MARK
        print("setting weight")
        for edge in G.edges():
            from_node, to_node = edge


            #@ RUN
            G.edges[edge]['weight'] = int(nodes_outbound[from_node].nx_weight)
            print("weight = nx_weight = cs_cost_total+TAX", nodes_outbound[from_node].name, int(nodes_outbound[from_node].nx_weight) )

            #@ STOP
            #G.edges[edge]['weight'] = int(nodes_outbound[from_node].cs_cost_total)
            #print("weight = cs_cost_total", nodes_outbound[from_node].name, int(nodes_outbound[from_node].cs_cost_total) )


        print("setting source and sink")

        # Total Supply Planの取得
        total_supply_plan = int( self.total_supply_plan )

        print("source:supply_point:-total_supply_plan", -total_supply_plan * scale_factor_demand)
        print("sink  :sales_office:total_supply_plan", total_supply_plan * scale_factor_demand)


        # scale = 1
        G.nodes['supply_point']['demand'] = -total_supply_plan * scale_factor_demand
        G.nodes['sales_office']['demand'] = total_supply_plan * scale_factor_demand


        print("optimizing supply chain network")

        for node in G.nodes():
            if node != 'supply_point' and node != 'sales_office':
                G.nodes[node]['demand'] = 0  # 他のノードのデマンドは0に設定



#        # ************************************
#        # optimize network
#        # ************************************
#        try:
#
#            flowCost_opt, flowDict_opt = nx.network_simplex(G)
#
#        except Exception as e:
#            print("Error during optimization:", e)
#            return
#
#        self.flowCost_opt = flowCost_opt
#        self.flowDict_opt = flowDict_opt
#
#        print("flowDict_opt", flowDict_opt)
#        print("flowCost_opt", flowCost_opt)
#
#        print("end optimization")




    def plan_through_engines4opt(self):

    #@RENAME
    # nodes_out_opt     : nodes_out_opt    
    # root_node_out_opt : root_node_out_opt


        print("planning with OPTIMIZED S")


        # Demand planning
        calc_all_psi2i4demand(self.root_node_out_opt)


        # Demand LEVELing on shipping yard / with pre_production week
        year_st = self.plan_year_st
        year_end = year_st + self.plan_range - 1
        pre_prod_week = self.pre_proc_LT
        demand_leveling_on_ship(self.root_node_out_opt, pre_prod_week, year_st, year_end)
        # root_node_out_optのsupplyの"PSI"を生成している
        self.root_node_out_opt.calcS2P_4supply()  #mother plantのconfirm S=> P
        self.root_node_out_opt.calcPS2I4supply()  #mother plantのPS=>I

        # ***************************************
        # その3　都度のparent searchを実行 setPS_on_ship2node
        # ***************************************
        feedback_psi_lists(self.root_node_out_opt, self.nodes_out_opt)



        #@241208 STOP
        ## Supply planning
        #print("Supply planning with Decoupling points")
        #nodes_decouple_all = make_nodes_decouple_all(self.root_node_out_opt)
        #print("nodes_decouple_all", nodes_decouple_all)
        #
        #for i, decouple_node_names in enumerate(nodes_decouple_all):
        #    decouple_flag = "OFF"
        #    if i == 0:

        decouple_node_names = self.decouple_node_selected

        push_pull_all_psi2i_decouple4supply5(self.root_node_out_opt, decouple_node_names)






# **** End of Optimization ****





    def load_tree_structure(self):
        try:
            file_path = filedialog.askopenfilename(title="Select Tree Structure File")
            if not file_path:
                return
            # Placeholder for loading tree structure
            self.tree_structure = nx.DiGraph()
            self.tree_structure.add_edge("Root", "Child1")
            self.tree_structure.add_edge("Root", "Child2")
            messagebox.showinfo("Success", "Tree structure loaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tree structure: {e}")




    def view_nx_matlib4opt(self):
        G = nx.DiGraph()
        Gdm_structure = nx.DiGraph()
        Gsp = nx.DiGraph()

        self.G = G
        self.Gdm_structure = Gdm_structure
        self.Gsp = Gsp

        pos_E2E, G, Gdm, Gsp = self.show_network_E2E_matplotlib(
            self.root_node_outbound, self.nodes_outbound,
            self.root_node_inbound, self.nodes_inbound,
            G, Gdm_structure, Gsp
        )

        self.pos_E2E = pos_E2E

        #self.draw_network4opt(G, Gdm, Gsp, pos_E2E)

        # グラフ描画関数を呼び出し  最適ルートを赤線で表示

        print("load_from_directory self.flowDict_opt", self.flowDict_opt)

        self.draw_network4opt(G, Gdm_structure, Gsp, pos_E2E, self.flowDict_opt)







    def draw_network4opt(self, G, Gdm, Gsp, pos_E2E, flowDict_opt):

        ## 既存の軸をクリア
        #self.ax_network.clear()

    #def draw_network(self, G, Gdm, Gsp, pos_E2E):

        self.ax_network.clear()  # 図をクリア


        print("draw_network4opt: self.total_revenue", self.total_revenue)
        print("draw_network4opt: self.total_profit", self.total_profit)

        # 評価結果の更新
        ttl_revenue = self.total_revenue
        ttl_profit = self.total_profit
        ttl_profit_ratio = (ttl_profit / ttl_revenue) if ttl_revenue != 0 else 0

        # 四捨五入して表示
        total_revenue = round(ttl_revenue)
        total_profit = round(ttl_profit)
        profit_ratio = round(ttl_profit_ratio * 100, 1)  # パーセント表示


        #ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=8)


        # タイトルを設定
        self.ax_network.set_title(f'PySI Optimized Supply Chain Network\nREVENUE: {total_revenue:,} | PROFIT: {total_profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=10)


        print("ax_network.set_title: total_revenue", total_revenue)
        print("ax_network.set_title: total_profit", total_profit)


#".format(total_revenue, total_profit))


        self.ax_network.axis('off')






        # *************************
        # contents of network draw START
        # *************************

        # ノードの形状と色を定義
        node_shapes = ['v' if node in self.decouple_node_selected else 'o' for node in G.nodes()]
        node_colors = ['brown' if node in self.decouple_node_selected else 'lightblue' for node in G.nodes()]


        # ノードの描画
        for node, shape, color in zip(G.nodes(), node_shapes, node_colors):

            nx.draw_networkx_nodes(G, pos_E2E, nodelist=[node], node_size=50, node_color=color, node_shape=shape, ax=self.ax_network)


        # エッジの描画
        for edge in G.edges():
            if edge[0] == "procurement_office" or edge[1] == "sales_office":
                edge_color = 'lightgrey'  # "procurement_office"または"sales_office"に接続するエッジはlightgrey
            elif edge in Gdm.edges():
                edge_color = 'blue'  # outbound（Gdm）のエッジは青
            elif edge in Gsp.edges():
                edge_color = 'green'  # inbound（Gsp）のエッジは緑
            else:
                edge_color = 'lightgrey'  # その他はlightgrey

            nx.draw_networkx_edges(G, pos_E2E, edgelist=[edge], edge_color=edge_color, arrows=False, ax=self.ax_network, width=0.5)

        # 最適化pathの赤線表示
        for from_node, flows in flowDict_opt.items():
            for to_node, flow in flows.items():
                if flow > 0:
                    # "G"の上に描画
                    nx.draw_networkx_edges(self.G, self.pos_E2E, edgelist=[(from_node, to_node)], ax=self.ax_network, edge_color='red', arrows=False, width=0.5)

        # ノードラベルの描画
        node_labels = {node: f"{node}" for node in G.nodes()}
        nx.draw_networkx_labels(G, pos_E2E, labels=node_labels, font_size=10, ax=self.ax_network)


        # *************************
        # contents of network draw END
        # *************************




        # ***************************
        # title and axis
        # ***************************
        #plt.title("Supply Chain Network end2end")

        #@ STOOOOOOOP
        #plt.title("Optimized Supply Chain Network")
        #self.ax_network.axis('off')  # 軸を非表示にする


        # *******************
        #@250319 STOP
        # *******************
        ## キャンバスを更新
        self.canvas_network.draw()



        # 🔴 `on_plot_click` 関数の定義（ここに追加）

        #info_window = None  # ノード情報ウィンドウの参照を保持

        # 🔴 `self.info_window` をクラス変数として定義
        self.info_window = None  # ノード情報ウィンドウの参照を保持

        def on_plot_click(event):
            """ クリックしたノードの情報を表示する関数 """
            #global info_window

            clicked_x, clicked_y = event.xdata, event.ydata

            print("clicked_x, clicked_y", clicked_x, clicked_y)

            if clicked_x is None or clicked_y is None:
                return  # クリックがグラフ外の場合は無視

            # クリック位置に最も近いノードを検索
            min_dist = float('inf')
            closest_node = None
            for node, (nx_pos, ny_pos) in pos_E2E.items():
                dist = np.sqrt((clicked_x - nx_pos) ** 2 + (clicked_y - ny_pos) ** 2)
                if dist < min_dist:
                    min_dist = dist
                    closest_node = node


            if closest_node and min_dist < 0.5:  # 誤認識を防ぐための閾値
            #if closest_node and min_dist < 0.1:  # 誤認識を防ぐための閾値
                node_info = f"Node: {closest_node}\nDegree: {G.degree[closest_node]}"

                print("closest_node", closest_node)




                # node情報の取り出し
                if closest_node in self.nodes_outbound:
                    if self.nodes_outbound[closest_node] is not None:
                        select_node = self.nodes_outbound[closest_node]
                    else:
                        print("error: nodes_outbound value is None")
                elif closest_node in self.nodes_inbound:
                    if self.nodes_inbound[closest_node] is not None:
                        select_node = self.nodes_inbound[closest_node]
                    else:
                        print("error: nodes_inbound value is None")
                else:
                    print("error: closest_node not found in nodes_outbound or nodes_inbound")

                



                #node_info = f' name: {select_node.name}\n leadtime: {select_node.leadtime}\n demand  : {select_node.nx_demand}\n weight  : {select_node.nx_weight}\n capacity: {select_node.nx_capacity }\n \n Evaluation\n decoupling_total_I: {select_node.decoupling_total_I }\n lot_counts_all    : {select_node.lot_counts_all     }\n \n Settings for cost-profit evaluation parameter}\n LT_boat            : {select_node.LT_boat             }\n SS_days            : {select_node.SS_days             }\n HS_code            : {select_node.HS_code             }\n customs_tariff_rate: {select_node.customs_tariff_rate }\n tariff_on_price    : {select_node.tariff_on_price     }\n price_elasticity   : {select_node.price_elasticity    }\n \n Business Perfirmance\n profit_ratio: {select_node.eval_profit_ratio     }%\n revenue     : {select_node.eval_revenue:,}\n profit      : {select_node.eval_profit:,}\n \n Cost_Structure\n PO_cost     : {select_node.eval_PO_cost        }\n P_cost      : {select_node.eval_P_cost         }\n WH_cost     : {select_node.eval_WH_cost        }\n SGMC        : {select_node.eval_SGMC           }\n Dist_Cost   : {select_node.eval_Dist_Cost      }'




                revenue = round(select_node.eval_cs_price_sales_shipped)
                profit = round(select_node.eval_cs_profit)

                # PROFIT_RATIOを計算して四捨五入
                profit_ratio = round((profit / revenue) * 100, 1) if revenue != 0 else 0


                SGA_total   = round(select_node.eval_cs_SGA_total)
                tax_portion = round(select_node.eval_cs_tax_portion)
                logi_costs  = round(select_node.eval_cs_logistics_costs)
                WH_cost     = round(select_node.eval_cs_warehouse_cost)
                Direct_MTRL = round(select_node.eval_cs_direct_materials_costs)




                node_info = (
    f" name: {select_node.name}\n"
    f" leadtime: {select_node.leadtime}\n"
    f" demand  : {select_node.nx_demand}\n"
    f" weight  : {select_node.nx_weight}\n"
    f" capacity: {select_node.nx_capacity }\n\n"
    f" Evaluation\n"
    f" decoupling_total_I: {select_node.decoupling_total_I }\n"
    f" lot_counts_all    : {select_node.lot_counts_all     }\n\n"
    f" Settings for cost-profit evaluation parameter\n"
    f" LT_boat            : {select_node.LT_boat             }\n"
    f" SS_days            : {select_node.SS_days             }\n"
    f" HS_code            : {select_node.HS_code             }\n"

    f" customs_tariff_rate: {select_node.customs_tariff_rate*100 }%\n"

    f" tariff_on_price    : {select_node.tariff_on_price     }\n"
    f" price_elasticity   : {select_node.price_elasticity    }\n\n"

    f" Business Performance\n"
    f" profit_ratio: {profit_ratio     }%\n"
    f" revenue     : {revenue:,}\n"
    f" profit      : {profit:,}\n\n"

    #f" profit_ratio: {select_node.eval_cs_profit_ratio     }%\n"
    #f" revenue     : {select_node.eval_cs_revenue:,}\n"
    #f" profit      : {select_node.eval_cs_profit:,}\n\n"


    #f" Tariff_ratio: {select_node.eval_cs_custom_tax}%\n" # これは意味なし

    f" Cost_Structure\n"
    f" SGA_total   : {SGA_total:,}\n"
    f" Custom_tax  : {tax_portion:,}\n"
    f" Logi_costs  : {logi_costs:,}\n"
    f" WH_cost     : {WH_cost:,}\n"
    f" Direct_MTRL : {Direct_MTRL:,}\n"
)


    #f" PO_cost     : {select_node.eval_cs_PO_cost        }\n"
    #f" P_cost      : {select_node.eval_cs_P_cost         }\n"
    #f" WH_cost     : {select_node.eval_cs_WH_cost        }\n"
    #f" SGMC        : {select_node.eval_cs_SGMC           }\n"
    #f" Dist_Cost   : {select_node.eval_cs_Dist_Cost      }"









                ax = self.ax_network

                # 🔴【修正1】 既存のラベルをクリア
                for text in ax.texts:
                    text.remove()

                # `node_info` をネットワーク・グラフの中央下部に固定表示
                #fixed_x, fixed_y = 0.5, 0.1  # Y座標を調整
                fixed_x, fixed_y = 0.5, 0  # Y座標を調整

                ax.text(fixed_x, fixed_y, node_info, fontsize=10, color="red",
                        transform=ax.transAxes, verticalalignment='bottom')




                ## `node_info` をネットワーク・グラフの固定領域に表示（中央下部
                #fixed_x, fixed_y = 0.5, -0.2  # グラフの中央下部に表示する座標（調整可能）
                #ax.text(fixed_x, fixed_y, node_info, fontsize=10, color="red",
                #        transform=ax.transAxes, verticalalignment='top')


                # `closest_node` をクリックしたノードの近くに表示
                ax.text(pos_E2E[closest_node][0], pos_E2E[closest_node][1], closest_node, fontsize=10, color="red")




                #@ STOP
                ## ノードの横に情報を表示
                #ax.text(pos_E2E[closest_node][0], pos_E2E[closest_node][1], node_info, fontsize=10, color="red")
                #
                #ax.text(pos_E2E[closest_node][0], pos_E2E[closest_node][1], closest_node, fontsize=10, color="red")




                # *************************
                # contents of network draw START
                # *************************

                # ノードの形状と色を定義
                node_shapes = ['v' if node in self.decouple_node_selected else 'o' for node in G.nodes()]
                node_colors = ['brown' if node in self.decouple_node_selected else 'lightblue' for node in G.nodes()]

                # ノードの描画
                for node, shape, color in zip(G.nodes(), node_shapes, node_colors):
                        nx.draw_networkx_nodes(G, pos_E2E, nodelist=[node], node_size=50, node_color=color, node_shape=shape, ax=self.ax_network)

                # エッジの描画
                for edge in G.edges():
                        if edge[0] == "procurement_office" or edge[1] == "sales_office":
                                edge_color = 'lightgrey'  # "procurement_office"または"sales_office"に接続するエッジはlightgrey
                        elif edge in Gdm.edges():
                                edge_color = 'blue'  # outbound（Gdm）のエッジは青
                        elif edge in Gsp.edges():
                                edge_color = 'green'  # inbound（Gsp）のエッジは緑
                        else:
                                edge_color = 'lightgrey'  # その他はlightgrey

                        nx.draw_networkx_edges(G, pos_E2E, edgelist=[edge], edge_color=edge_color, arrows=False, ax=self.ax_network, width=0.5)

                # 最適化pathの赤線表示
                for from_node, flows in flowDict_opt.items():
                        for to_node, flow in flows.items():
                                if flow > 0:
                                        # "G"の上に描画
                                        nx.draw_networkx_edges(self.G, self.pos_E2E, edgelist=[(from_node, to_node)], ax=self.ax_network, edge_color='red', arrows=False, width=0.5)

                # ノードラベルの描画
                node_labels = {node: f"{node}" for node in G.nodes()}
                nx.draw_networkx_labels(G, pos_E2E, labels=node_labels, font_size=10, ax=self.ax_network)

                # *************************
                # contents of network draw END
                # *************************




                #canvas.draw()  # 再描画
                self.canvas_network.draw()  # 再描画





                # 🔴【修正2】 既存のウィンドウを閉じる
                if self.info_window is not None:
                    self.info_window.destroy()

                # 新しい情報ウィンドウを作成

                show_info_graph(node_info, select_node)
                #self.show_info_graph(node_info, select_node)
                #show_info_graph(node_info)





        def show_info_graph(node_info, select_node):
                """ ノード情報を表示する Tkinter ウィンドウ + 円グラフ """
                if self.info_window is not None:
                        self.info_window.destroy()
                
                self.info_window = tk.Toplevel(self.root)
                self.info_window.title("Node Information")
                
                labels = ['Profit', 'SG&A', 'Tax Portion', 'Logistics', 'Warehouse', 'Materials']
                values = [
                        select_node.eval_cs_profit,
                        select_node.eval_cs_SGA_total,
                        select_node.eval_cs_tax_portion,
                        select_node.eval_cs_logistics_costs,
                        select_node.eval_cs_warehouse_cost,
                        select_node.eval_cs_direct_materials_costs,
                ]
                
                colors = ['blue', 'orange', 'green', 'red', 'purple', 'brown']  # 各項目の固定色
                
                # 売上（収益）から非ゼロ構成のみ抽出
                filtered = [(label, val, color) for label, val, color in zip(labels, values, colors) if val > 0]
                if not filtered:
                        filtered = [('No Data', 1, 'gray')]
                
                labels, values, colors = zip(*filtered)
                
                fig, ax = plt.subplots(figsize=(5, 4))
                ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors)
                ax.set_title(select_node.name, fontsize=9)  # `node_info` ではなく `node_name` をタイトルに設定
                
                #ax.set_title(node_info, fontsize=9)  # `node_info` ではなく `node_name` をタイトルに設定
                


                # Tkinter の Frame に Matplotlib のグラフと node_info を配置
                frame = tk.Frame(self.info_window)
                frame.pack()
                
                canvas = FigureCanvasTkAgg(fig, frame)
                canvas.get_tk_widget().grid(row=0, column=0)
                canvas.draw()
                
                # node_info を右横に表示
                info_label = tk.Label(frame, text=node_info, justify='left', padx=10, font=("Arial", 10), fg='darkblue')
                info_label.grid(row=0, column=1, sticky='nw')


                #info_label = tk.Label(frame, text=node_info, justify='left', padx=10, font=("Arial", 10))
                #info_label.grid(row=0, column=1, sticky='nw')



                #canvas = FigureCanvasTkAgg(fig, self.info_window)
                #canvas.get_tk_widget().pack()
                #canvas.draw()





        def show_info_graph_OLD2(node_info, select_node):
        #def show_info_graph(self, node_info, select_node):
                """ ノード情報を表示する Tkinter ウィンドウ + 円グラフ """

                if self.info_window is not None:
                        self.info_window.destroy()

                self.info_window = tk.Toplevel(self.root)
                self.info_window.title("Node Information")

                # 円グラフデータを準備
                labels = [
                        'Profit',
                        'SG&A',

                        #'Custom Tax',

                        'Tax Portion',
                        'Logistics',
                        'Warehouse',
                        'Materials',
                ]
                values = [
                        select_node.eval_cs_profit,
                        select_node.eval_cs_SGA_total,

                        #select_node.eval_cs_custom_tax,

                        select_node.eval_cs_tax_portion,
                        select_node.eval_cs_logistics_costs,
                        select_node.eval_cs_warehouse_cost,
                        select_node.eval_cs_direct_materials_costs,
                ]

                # 売上（収益）から非ゼロ構成のみ抽出
                filtered = [(label, val) for label, val in zip(labels, values) if val > 0]
                if not filtered:
                        filtered = [('No Data', 1)]

                labels, values = zip(*filtered)

                # グラフ作成
                fig, ax = plt.subplots(figsize=(5, 4))
                ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
                ax.set_title(node_info, fontsize=9)

                canvas = FigureCanvasTkAgg(fig, self.info_window)
                canvas.get_tk_widget().pack()
                canvas.draw()



        def show_info_graph_OLD(node_info):
            """ ノード情報を表示する Tkinter ウィンドウ """
            #global info_window

            self.info_window = tk.Toplevel(self.root)
            self.info_window.title("Node Information")

            # 新しいグラフを描画
            fig_info, ax_info = plt.subplots(figsize=(4, 3))
            ax_info.bar([1], [1], color='orange')  # 仮データ
            ax_info.set_title(node_info)

            canvas_info = FigureCanvasTkAgg(fig_info, self.info_window)
            canvas_info.get_tk_widget().pack()
            canvas_info.draw()

        # 🔴 `mpl_connect` でクリックイベントを登録（ここに追加）
        #canvas.mpl_connect('button_press_event', on_plot_click)
        self.canvas_network.mpl_connect('button_press_event', on_plot_click)



        #@STOP
        ## Tkinter メインループ開始
        #self.root.mainloop()













    def view_nx_matlib(self):
        G = nx.DiGraph()
        Gdm_structure = nx.DiGraph()
        Gsp = nx.DiGraph()

        print(f"view_nx_matlib before show_network_E2E_matplotlib self.decouple_node_selected: {self.decouple_node_selected}")

        pos_E2E, G, Gdm_structure, Gsp = self.show_network_E2E_matplotlib(
            self.root_node_outbound, self.nodes_outbound,
            self.root_node_inbound, self.nodes_inbound,
            G, Gdm_structure, Gsp
        )

        self.pos_E2E = pos_E2E

        print(f"view_nx_matlib after show_network_E2E_matplotlib self.decouple_node_selected: {self.decouple_node_selected}")

        self.G = G
        self.Gdm_structure = Gdm_structure
        self.Gsp = Gsp

        self.draw_network(self.G, self.Gdm_structure, self.Gsp, self.pos_E2E)



    def draw_network(self, G, Gdm, Gsp, pos_E2E):
        self.ax_network.clear()  # 図をクリア

        # 評価結果の更新
        ttl_revenue = self.total_revenue
        ttl_profit = self.total_profit
        ttl_profit_ratio = (ttl_profit / ttl_revenue) if ttl_revenue != 0 else 0

        # 四捨五入して表示
        total_revenue = round(ttl_revenue)
        total_profit = round(ttl_profit)
        profit_ratio = round(ttl_profit_ratio * 100, 1)  # パーセント表示

        # タイトルを設定
        self.ax_network.set_title(f'PySI\nOptimized Supply Chain Network\nREVENUE: {total_revenue:,} | PROFIT: {total_profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=10)

        self.ax_network.axis('off')

        print("draw_network self.decouple_node_selected", self.decouple_node_selected)
        print("draw_network G nodes", list(G.nodes()))
        print("draw_network G edges", list(G.edges()))

        # Node描画
        node_shapes = ['v' if node in self.decouple_node_selected else 'o' for node in G.nodes()]
        node_colors = ['brown' if node in self.decouple_node_selected else 'lightblue' for node in G.nodes()]

        for node, shape, color in zip(G.nodes(), node_shapes, node_colors):
            nx.draw_networkx_nodes(G, pos_E2E, nodelist=[node], node_size=50, node_color=color, node_shape=shape, ax=self.ax_network)





        # Edge描画
        for edge in G.edges():
            edge_color = 'lightgrey' if edge[0] == "procurement_office" or edge[1] == "sales_office" else 'blue' if edge in Gdm.edges() else 'green' if edge in Gsp.edges() else 'gray'
            nx.draw_networkx_edges(G, pos_E2E, edgelist=[edge], edge_color=edge_color, arrows=False, ax=self.ax_network, width=0.5)

        # Labels描画
        node_labels = {node: node for node in G.nodes()}
        nx.draw_networkx_labels(G, pos_E2E, labels=node_labels, font_size=10, ax=self.ax_network) #@250702 fantsize 6=>10


        #@ STOP
        ## キャンバスの再描画
        #self.canvas_network.draw()

        # キャンバスの再描画
        # 描画処理を待機キューに入れて部分的な描画を実行
        self.canvas_network.draw_idle()





    def display_decoupling_patterns(self):
        subroot = tk.Toplevel(self.root)
        subroot.title("Decoupling Stock Buffer Patterns")

        frame = ttk.Frame(subroot)
        frame.pack(fill='both', expand=True)

        tree = ttk.Treeview(frame, columns=('Revenue', 'Profit', 'Nodes'), show='headings')
        tree.heading('Revenue', text='Revenue')
        tree.heading('Profit', text='Profit')
        tree.heading('Nodes', text='Nodes')
        tree.pack(fill='both', expand=True)

        style = ttk.Style()
        # カラムヘッダを中央揃えにする
        style.configure('Treeview.Heading', anchor='center')

        style.configure('Treeview', rowheight=25)  # 行の高さを設定

        def format_number(value):
            return f"{round(value):,}"

        for i, (revenue, profit, nodes) in self.decouple_node_dic.items():
            formatted_revenue = format_number(revenue)
            formatted_profit = format_number(profit)
            tree.insert('', 'end', values=(formatted_revenue, formatted_profit, ', '.join(nodes)))

        # 列を右寄せに設定する関数
        def adjust_column(tree, col):
            tree.column(col, anchor='e')

        # Revenue と Profit の列を右寄せに設定
        adjust_column(tree, 'Revenue')
        adjust_column(tree, 'Profit')

        selected_pattern = None

        def on_select_pattern(event):
            nonlocal selected_pattern
            item = tree.selection()[0]
            selected_pattern = tree.item(item, 'values')

        tree.bind('<<TreeviewSelect>>', on_select_pattern)

        def on_confirm():
            if selected_pattern:
                self.decouple_node_selected = selected_pattern[2].split(', ')

                print("decouple_node_selected", self.decouple_node_selected)
                self.execute_selected_pattern()

                subroot.destroy()  # サブウィンドウを閉じる

        confirm_button = ttk.Button(subroot, text="SELECT buffering stock", command=on_confirm)
        confirm_button.pack()

        subroot.protocol("WM_DELETE_WINDOW", on_confirm)








    def execute_selected_pattern(self):
        decouple_node_names = self.decouple_node_selected

        # PSI計画の状態をリストア
        self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')

        print("exe engine decouple_node_selected", self.decouple_node_selected)

        push_pull_all_psi2i_decouple4supply5(self.root_node_outbound, decouple_node_names)

        self.update_evaluation_results()

        self.view_nx_matlib()
        self.root.after(1000, self.show_psi("outbound", "supply"))




    def load4execute_selected_pattern(self):


        # 1. Load元となるdirectoryの問い合わせ
        load_directory = filedialog.askdirectory()
        if not load_directory:
            return  # ユーザーがキャンセルした場合

        ## 2. 初期処理のcsv fileのコピー
        #for filename in os.listdir(load_directory):
        #    if filename.endswith('.csv'):
        #        full_file_name = os.path.join(load_directory, filename)
        #        if os.path.isfile(full_file_name):
        #            shutil.copy(full_file_name, self.directory)

        # 3. Tree構造の読み込み
        with open(os.path.join(load_directory, 'root_node_outbound.pkl'), 'rb') as f:
            self.root_node_outbound = pickle.load(f)
            print(f"root_node_outbound loaded: {self.root_node_outbound.name}")

        #
        #with open(os.path.join(load_directory, 'root_node_inbound.pkl'), 'rb') as f:
        #    self.root_node_inbound = pickle.load(f)
        #    print(f"root_node_inbound loaded: {self.root_node_inbound}")

        # 4. PSIPlannerAppのデータ・インスタンスの読み込み
        with open(os.path.join(load_directory, 'psi_planner_app.pkl'), 'rb') as f:
            loaded_attributes = pickle.load(f)
            self.__dict__.update(loaded_attributes)
            print(f"loaded_attributes: {loaded_attributes}")

        ## 5. nodes_outboundとnodes_inboundを再生成
        #self.nodes_outbound = self.regenerate_nodes(self.root_node_outbound)
        #self.nodes_inbound = self.regenerate_nodes(self.root_node_inbound)

        # network area
        print("load_from_directory self.decouple_node_selected", self.decouple_node_selected)



        #decouple_node_names = self.decouple_node_selected





        decouple_node_names = self.decouple_node_selected

        ## PSI計画の状態をリストア
        #self.root_node_outbound = self.psi_restore_from_file('psi_backup.pkl')

        print("exe engine decouple_node_selected", self.decouple_node_selected)

        push_pull_all_psi2i_decouple4supply5(self.root_node_outbound, decouple_node_names)

        self.update_evaluation_results()


        #@241212 Gdm_structureにupdated
        self.draw_network(G, Gdm_structure, Gsp, pos_E2E)

        ## 追加: キャンバスを再描画
        #self.canvas_network.draw()
        #
        #self.view_nx_matlib()

        self.root.after(1000, self.show_psi("outbound", "supply"))




# ******************************************
# clear_s_values
# ******************************************
#
#複数年のデータに対応するために、node_name と year をキーにして各ノードのデータを処理。
#
#説明
#leaf_nodeの特定方法の修正：
#
#flow_dict 内で各ノードに sales_office が含まれているかどうかで leaf_nodes を特定します。
#
#rule-1, rule-2, rule-3 の適用：
#
#rule-1: flow_dict に存在しないノードの月次Sの値を0に設定。
#
#rule-2: flow_dict に存在し、sales_office に繋がるノードの値が0である場合、月次S#の値を0に設定。
#
#rule-3: flow_dict に存在し、sales_office に繋がるノードの値が0以外である場合、月次Sの値をプロポーションに応じて分配。
#
#proportionsの計算と値の丸め：
#
#各月のproportionを計算し、それを使って丸めた値を求めます。
#
#rounded_values に丸めた値を格納し、合計が期待する供給量と一致しない場合は、
#最大の値を持つ月で調整します。
#
#年間total_supplyが0の場合の処理：
#年間total_supplyが0の場合は、月次Sの値をすべて0に設定します。


    def clear_s_values(self, flow_dict, input_csv, output_csv):
        # 1. 入力ファイルS_month_data.csvをデータフレームに読み込み
        df = pd.read_csv(input_csv)

        # leaf_nodeを特定
        leaf_nodes = [node for node, connections in flow_dict.items() if 'sales_office' in connections]

        # 2. rule-1, rule-2, rule-3を適用してデータを修正する
        for index, row in df.iterrows():
            node_name = row['node_name']
            year = row['year']
            
            if node_name in flow_dict:
                # ノードがflow_dictに存在する場合
                if node_name in leaf_nodes:
                    # rule-2: ノードの値が0の場合、月次Sの値をすべて0に設定
                    if flow_dict[node_name]['sales_office'] == 0:
                        df.loc[(df['node_name'] == node_name) & (df['year'] == year),
                               ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']] = 0
                    else:
                        # rule-3: ノードの値が0以外の場合、月次Sのproportionに応じて分配
                        total_supply = sum(df.loc[(df['node_name'] == node_name) & (df['year'] == year), 
                                                  ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']].values.flatten())
                        if total_supply != 0:
                            proportions = df.loc[(df['node_name'] == node_name) & (df['year'] == year), 
                                                 ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']].values.flatten() / total_supply
                            rounded_values = [round(proportion * flow_dict[node_name]['sales_office']) for proportion in proportions]
                            difference = flow_dict[node_name]['sales_office'] - sum(rounded_values)
                            if difference != 0:
                                max_index = rounded_values.index(max(rounded_values))
                                rounded_values[max_index] += difference
                            df.loc[(df['node_name'] == node_name) & (df['year'] == year),
                                   ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']] = rounded_values
                        else:
                            # 供給量がゼロの場合、元データを保持（エラーチェック）
                            df.loc[(df['node_name'] == node_name) & (df['year'] == year), 
                                   ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']] = [0] * 12
            else:
                # rule-1: ノードがflow_dictに存在しない場合、月次Sの値をすべて0に設定
                df.loc[index, ['m1', 'm2', 'm3', 'm4', 'm5', 'm6', 'm7', 'm8', 'm9', 'm10', 'm11', 'm12']] = 0

        # 3. 結果を"S_month_data_optimized.csv"として保存する
        df.to_csv(output_csv, index=False)
        print(f"Optimized data saved to {output_csv}")




    def view_nx_matlib4opt_OLD(self):
        try:
            if self.tree_structure is None:
                raise ValueError("Tree structure is not loaded.")

            self.ax_network.clear()
            nx.draw(self.tree_structure, with_labels=True, ax=self.ax_network)
            self.canvas_network.draw()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to display optimization graph: {e}")








    def eval_supply_chain_cost4opt(self, node_opt):
    
        # change from "out_opt" to "outbound"
        node = self.nodes_outbound[node_opt.name]

        # *********************
        # counting Purchase Order
        # *********************
        # psi_listのPOは、psi_list[w][3]の中のlot_idのロット数=リスト長

        # lot_counts is "out_opt"side
        node_opt.set_lot_counts()

        #@ STOP
        #node.set_lot_counts()
    
        # output:
        #    self.lot_counts_all = sum(self.lot_counts)

        # change lot_counts from "out_opt"side to "outbound"side
        node.lot_counts_all = node_opt.lot_counts_all
    
        # *********************
        # EvalPlanSIP()の中でnode instanceに以下をセットする
        # self.profit, self.revenue, self.profit_ratio
        # *********************
    
        # by weekの計画状態xxx[w]の変化を評価して、self.eval_xxxにセット
        total_revenue, total_profit = node.EvalPlanSIP_cost()

    
        #@241225 ADD
        node.total_revenue     = total_revenue    
        node.total_profit      = total_profit     
                                 
        node_opt.total_revenue = total_revenue
        node_opt.total_profit  = total_profit 
                                 
        self.total_revenue += total_revenue
        self.total_profit  += total_profit
    
    
        #@241118 "eval_" is 1st def /  "eval_cs_" is 2nd def
        # print(
        #    "Eval node profit revenue profit_ratio",
        #    node.name,
        #    node.eval_profit,
        #    node.eval_revenue,
        #    node.eval_profit_ratio,
        # )
    
        for child in node.children:
    
            self.eval_supply_chain_cost4opt(child)





#@250218 STOP
#    def cash_flow_print(self):
#
#        #self.total_revenue, self.total_profit = eval_supply_chain_cost(self.root_node_outbound)
#
#        self.total_revenue, self.total_profit = eval_supply_chain_cash(self.root_node_outbound)




    def update_evaluation_results(self):


        # Evaluation on PSI
        self.total_revenue = 0
        self.total_profit  = 0
        self.profit_ratio  = 0


        # ***********************
        # This is a simple Evaluation process with "cost table"
        # ***********************


#@241120 STOP
#        self.eval_plan()
#
#    def eval_plan(self):



        # 在庫係数の計算
        # I_cost_coeff = I_total_qty_init / I_total_qty_planned
        #
        # 計画された在庫コストの算定
        # I_cost_planned = I_cost_init * I_cost_coeff
    
    
        # by node evaluation Revenue / Cost / Profit
        # "eval_xxx" = "lot_counts" X "cs_xxx" that is from cost_table
        # Inventory cost has 係数 = I_total on Demand/ I_total on Supply
    
    
        #self.total_revenue = 0
        #self.total_profit  = 0
    
        #eval_supply_chain_cost(self.root_node_outbound)
        #self.eval_supply_chain_cost(self.root_node_outbound)
    
        #eval_supply_chain_cost(self.root_node_inbound)
        #self.eval_supply_chain_cost(self.root_node_inbound)

        #@ CONTEXT グローバル変数 STOP
        ## サプライチェーン全体のコストを評価
        #eval_supply_chain_cost(self.root_node_outbound, self)
        #eval_supply_chain_cost(self.root_node_inbound, self)




        # サプライチェーンの評価を開始

        # tree.py に配置して、node に対して：
        # set_lot_counts() を呼び出し、ロット数を設定
        # EvalPlanSIP_cost() で revenue と profit を計算
        # 子ノード (children) に対して再帰的に eval_supply_chain_cost() をcall

        self.total_revenue, self.total_profit = eval_supply_chain_cost(self.root_node_outbound)



        ttl_revenue = self.total_revenue
        ttl_profit  = self.total_profit

        if ttl_revenue == 0:
            ttl_profit_ratio = 0
        else:
            ttl_profit_ratio = ttl_profit / ttl_revenue

        # 四捨五入して表示 
        total_revenue = round(ttl_revenue) 
        total_profit = round(ttl_profit) 
        profit_ratio = round(ttl_profit_ratio*100, 1) # パーセント表示

        print("total_revenue", total_revenue)
        print("total_profit", total_profit)
        print("profit_ratio", profit_ratio)


#total_revenue 343587
#total_profit 32205
#profit_ratio 9.4


        self.total_revenue_entry.config(state='normal')
        self.total_revenue_entry.delete(0, tk.END)
        self.total_revenue_entry.insert(0, f"{total_revenue:,}")
        #self.total_revenue_entry.insert(0, str(kpi_results["total_revenue"]))
        self.total_revenue_entry.config(state='readonly')


        self.total_profit_entry.config(state='normal')
        self.total_profit_entry.delete(0, tk.END)
        self.total_profit_entry.insert(0, f"{total_profit:,}")
        #self.total_profit_entry.insert(0, str(kpi_results["total_profit"]))
        self.total_profit_entry.config(state='readonly')


        self.profit_ratio_entry.config(state='normal')
        self.profit_ratio_entry.delete(0, tk.END)
        self.profit_ratio_entry.insert(0, f"{profit_ratio}%")
        self.profit_ratio_entry.config(state='readonly')

        # 画面を再描画
        self.total_revenue_entry.update_idletasks()
        self.total_profit_entry.update_idletasks()
        self.profit_ratio_entry.update_idletasks()





    def update_evaluation_results4optimize(self):


        # Evaluation on PSI
        self.total_revenue = 0
        self.total_profit  = 0
        self.profit_ratio  = 0


        # ***********************
        # This is a simple Evaluation process with "cost table"
        # ***********************


        # 在庫係数の計算
        # I_cost_coeff = I_total_qty_init / I_total_qty_planned
        #
        # 計画された在庫コストの算定
        # I_cost_planned = I_cost_init * I_cost_coeff
    
    
        # by node evaluation Revenue / Cost / Profit
        # "eval_xxx" = "lot_counts" X "cs_xxx" that is from cost_table
        # Inventory cost has 係数 = I_total on Demand/ I_total on Supply
    
    
        #self.total_revenue = 0
        #self.total_profit  = 0
    


        #@241225 memo "root_node_out_opt"のtreeにはcs_xxxxがセットされていない
        # cs_xxxxのあるnode = self.nodes_outbound[node_opt.name]に変換して参照
        #@241225 be checkek
        # ***************************
        # change ROOT HANDLE
        # ***************************
        self.eval_supply_chain_cost4opt(self.root_node_out_opt)

        print("self.root_node_out_opt.name", self.root_node_out_opt.name)

        #self.eval_supply_chain_cost(self.root_node_outbound)
        #self.eval_supply_chain_cost(self.root_node_inbound)

        ttl_revenue = self.total_revenue
        ttl_profit  = self.total_profit

        print("def update_evaluation_results4optimize")
        print("self.total_revenue", self.total_revenue)
        print("self.total_profit" , self.total_profit)


        if ttl_revenue == 0:
            ttl_profit_ratio = 0
        else:
            ttl_profit_ratio = ttl_profit / ttl_revenue

        # 四捨五入して表示 
        total_revenue = round(ttl_revenue) 
        total_profit = round(ttl_profit) 
        profit_ratio = round(ttl_profit_ratio*100, 1) # パーセント表示

        print("total_revenue", total_revenue)
        print("total_profit", total_profit)
        print("profit_ratio", profit_ratio)


#total_revenue 343587
#total_profit 32205
#profit_ratio 9.4


        self.total_revenue_entry.config(state='normal')
        self.total_revenue_entry.delete(0, tk.END)
        self.total_revenue_entry.insert(0, f"{total_revenue:,}")
        #self.total_revenue_entry.insert(0, str(kpi_results["total_revenue"]))
        self.total_revenue_entry.config(state='readonly')


        self.total_profit_entry.config(state='normal')
        self.total_profit_entry.delete(0, tk.END)
        self.total_profit_entry.insert(0, f"{total_profit:,}")
        #self.total_profit_entry.insert(0, str(kpi_results["total_profit"]))
        self.total_profit_entry.config(state='readonly')


        self.profit_ratio_entry.config(state='normal')
        self.profit_ratio_entry.delete(0, tk.END)
        self.profit_ratio_entry.insert(0, f"{profit_ratio}%")
        self.profit_ratio_entry.config(state='readonly')

        # 画面を再描画
        self.total_revenue_entry.update_idletasks()
        self.total_profit_entry.update_idletasks()
        self.profit_ratio_entry.update_idletasks()




# ******************************************
# visualize graph
# ******************************************

    def view_nx_matlib_stop_draw(self):
        G = nx.DiGraph()
        Gdm_structure = nx.DiGraph()
        Gsp = nx.DiGraph()

        print(f"view_nx_matlib before show_network_E2E_matplotlib self.decouple_node_selected: {self.decouple_node_selected}")

        pos_E2E, G, Gdm_structure, Gsp = self.show_network_E2E_matplotlib(
            self.root_node_outbound, self.nodes_outbound,
            self.root_node_inbound, self.nodes_inbound,
            G, Gdm_structure, Gsp
        )

        self.pos_E2E = pos_E2E

        print(f"view_nx_matlib after show_network_E2E_matplotlib self.decouple_node_selected: {self.decouple_node_selected}")

        self.G = G
        self.Gdm_structure = Gdm_structure
        self.Gsp = Gsp

        #@250106 STOP draw
        #self.draw_network(self.G, self.Gdm_structure, self.Gsp, self.pos_E2E)



    def initialize_graphs(self):
        self.G = nx.DiGraph()
        self.Gdm_structure = nx.DiGraph()
        self.Gsp = nx.DiGraph()


    # ***************************
    # make network with NetworkX
    # ***************************



    def show_network_E2E_matplotlib(self,
            root_node_outbound, nodes_outbound, 
            root_node_inbound, nodes_inbound, 
            G, Gdm, Gsp):
        
        # Original code's logic to process and set up the network
        root_node_name_out = root_node_outbound.name 
        root_node_name_in  = root_node_inbound.name

        total_demand =0
        total_demand = set_leaf_demand(root_node_outbound, total_demand)
        #total_demand = self.set_leaf_demand(root_node_outbound, total_demand)
        print("average_total_demand", total_demand)
        print("root_node_outbound.nx_demand", root_node_outbound.nx_demand)

        root_node_outbound.nx_demand = total_demand  
        root_node_inbound.nx_demand = total_demand  

        G_add_nodes_from_tree(root_node_outbound, G)
        #self.G_add_nodes_from_tree(root_node_outbound, G)
        G_add_nodes_from_tree_skip_root(root_node_inbound, root_node_name_in, G)
        #self.G_add_nodes_from_tree_skip_root(root_node_inbound, root_node_name_in, G)

        G.add_node("sales_office", demand=total_demand)
        G.add_node(root_node_outbound.name, demand=0)
        G.add_node("procurement_office", demand=(-1 * total_demand))

        G_add_edge_from_tree(root_node_outbound, G)
        #self.G_add_edge_from_tree(root_node_outbound, G)
        supplyers_capacity = root_node_inbound.nx_demand * 2 
        G_add_edge_from_inbound_tree(root_node_inbound, supplyers_capacity, G)
        #self.G_add_edge_from_inbound_tree(root_node_inbound, supplyers_capacity, G)

        G_add_nodes_from_tree(root_node_outbound, Gdm)
        #self.G_add_nodes_from_tree(root_node_outbound, Gdm)
        Gdm.add_node(root_node_outbound.name, demand = (-1 * total_demand))
        Gdm.add_node("sales_office", demand = total_demand)
        Gdm_add_edge_sc2nx_outbound(root_node_outbound, Gdm)
        #self.Gdm_add_edge_sc2nx_outbound(root_node_outbound, Gdm)

        G_add_nodes_from_tree(root_node_inbound, Gsp)
        #self.G_add_nodes_from_tree(root_node_inbound, Gsp)
        Gsp.add_node("procurement_office", demand = (-1 * total_demand))
        Gsp.add_node(root_node_inbound.name, demand = total_demand)
        Gsp_add_edge_sc2nx_inbound(root_node_inbound, Gsp)
        #self.Gsp_add_edge_sc2nx_inbound(root_node_inbound, Gsp)

        pos_E2E = make_E2E_positions(root_node_outbound, root_node_inbound)
        #pos_E2E = self.make_E2E_positions(root_node_outbound, root_node_inbound)
        pos_E2E = tune_hammock(pos_E2E, nodes_outbound, nodes_inbound)
        #pos_E2E = self.tune_hammock(pos_E2E, nodes_outbound, nodes_inbound)

        return pos_E2E, G, Gdm, Gsp



    def show_network_E2E_matplotlib_with_self(self):
        root_node_outbound = self.root_node_outbound
        nodes_outbound = self.nodes_outbound
        root_node_inbound = self.root_node_inbound
        nodes_inbound = self.nodes_inbound
        return self.show_network_E2E_matplotlib(
            root_node_outbound, nodes_outbound, 
            root_node_inbound, nodes_inbound, 
            self.G, self.Gdm_structure, self.Gsp
        )


# ******************************************
# optimize network graph
# ******************************************


    def optimize(self, G_opt):
        self.reset_optimization_params(G_opt)
        self.set_optimization_params(G_opt)
        self.run_optimization(G_opt)
        print("run_optimization self.flowDict_opt", self.flowDict_opt)
        self.reset_optimized_path(G_opt)
        self.add_optimized_path(G_opt, self.flowDict_opt)
        print("Optimized Path:", self.flowDict_opt)
        print("Optimized Cost:", self.flowCost_opt)





    def load_data_files4opt(self):

    #@RENAME
    # nodes_outbound     : nodes_out_opt    
    # root_node_outbound : root_node_out_opt


        # setting directory from "plan"
        directory = self.directory


        #@ STOP
        #directory = filedialog.askdirectory(title="Select Data Directory")


        if directory:

            # ***********************
            # Lot sizeを取得して変換
            # ***********************
            #try:
            #    self.lot_size = int(self.lot_size_entry.get())
            #except ValueError:
            #    print("Invalid lot size input. Using default value.")

            # Lot size, Plan Year Start, and Plan Rangeを取得して変換
            try:
                self.lot_size = int(self.lot_size_entry.get())
                self.plan_year_st = int(self.plan_year_entry.get())
                self.plan_range = int(self.plan_range_entry.get())
            except ValueError:
                print("Invalid input for lot size, plan year start, or plan range. Using default values.")

            self.outbound_data = []
            self.inbound_data = []

            print("os.listdir(directory)",os.listdir(directory))

            data_file_list = os.listdir(directory)


            # save directory
            self.directory = directory


            # ************************
            # read "profile_tree_outbound.csv"
            # build tree_outbound
            # ************************
            if "profile_tree_outbound.csv" in data_file_list:

                filename = "profile_tree_outbound.csv"

                file_path = os.path.join(directory, filename)
                #filepath = os.path.join(directory, filename)


                #load_outbound(outbound_tree_file)


                # ***************************
                # set file name for "profile tree"
                # ***************************
                #outbound_tree_file = "profile_tree_outbound.csv"
                #inbound_tree_file = "profile_tree_inbound.csv"

                # ***************************
                # create supply chain tree for "out"bound + optimization
                # ***************************

                # because of the python interpreter performance point of view,
                # this "create tree" code be placed in here, main process

            #@240830
            # "nodes_xxxx" is dictionary to get "node pointer" from "node name"
                nodes_out_opt = {}
                nodes_out_opt, root_node_name_out = create_tree_set_attribute(file_path)

                print("root_node_name_out",root_node_name_out)

                root_node_out_opt = nodes_out_opt[root_node_name_out]




                def make_leaf_nodes(node, list):
                    if node.children == []: # leaf_nodeの場合
                        list.append(node.name)
                    else:
                        pass

                    for child in node.children:
                        make_leaf_nodes(child, list)

                    return list

                leaf_nodes_opt = []
                leaf_nodes_opt = make_leaf_nodes(root_node_out_opt, leaf_nodes_opt)



                # making balance for nodes



                # ********************************
                # set outbound tree handle
                # ********************************
                self.nodes_out_opt = nodes_out_opt
                self.root_node_out_opt = root_node_out_opt


                print("leaf_nodes_opt", leaf_nodes_opt)
                self.leaf_nodes_opt = leaf_nodes_opt

                # ********************************
                # tree wideth/depth count and adjust
                # ********************************
                set_positions(root_node_out_opt)



                # root_node_out_opt = nodes_out_opt['JPN']      # for test, direct define
                # root_node_out_opt = nodes_out_opt['JPN_OUT']  # for test, direct define

                # setting parent on its child
                set_parent_all(root_node_out_opt)
                print_parent_all(root_node_out_opt)

            else:
                print("error: profile_tree_outbound.csv is missed")
                pass


            # ************************
            # read "profile_tree_inbound.csv"
            # build tree_inbound
            # ************************
            if "profile_tree_inbound.csv" in data_file_list:

                filename = "profile_tree_inbound.csv"
                file_path = os.path.join(directory, filename)


                # ***************************
                # create supply chain tree for "in"bound
                # ***************************
                nodes_inbound = {}

                nodes_inbound, root_node_name_in = create_tree_set_attribute(file_path)
                root_node_inbound = nodes_inbound[root_node_name_in]


                # ********************************
                # set inbound tree handle
                # ********************************
                self.nodes_inbound = nodes_inbound
                self.root_node_inbound = root_node_inbound


                # ********************************
                # tree wideth/depth count and adjust
                # ********************************
                set_positions(root_node_inbound)

                # setting parent on its child
                set_parent_all(root_node_inbound)
                print_parent_all(root_node_inbound)

            else:
                print("error: profile_tree_inbound.csv is missed")

                pass




            # ************************
            # read "node_cost_table_outbound.csv"
            # read_set_cost
            # ************************
            if "node_cost_table_outbound.csv" in data_file_list:

                filename = "node_cost_table_outbound.csv"
                file_path = os.path.join(directory, filename)

                read_set_cost(file_path, nodes_out_opt)

            else:
                print("error: node_cost_table_outbound.csv is missed")

                pass




            # ************************
            # read "node_cost_table_inbound.csv"
            # read_set_cost
            # ************************
            if "node_cost_table_inbound.csv" in data_file_list:

                filename = "node_cost_table_inbound.csv"
                file_path = os.path.join(directory, filename)

                read_set_cost(file_path, nodes_inbound)


            else:
                print("error: node_cost_table_inbound.csv is missed")

                pass









            # ***************************
            # make price chain table
            # ***************************

            # すべてのパスを見つける
            paths = find_paths(root_node_out_opt)

            # 各リストをタプルに変換してsetに変換し、重複を排除
            unique_paths = list(set(tuple(x) for x in paths))

            # タプルをリストに戻す
            unique_paths = [list(x) for x in unique_paths]

            print("")
            print("")

            for path in unique_paths:
                print(path)

            sorted_paths = sorted(paths, key=len)

            print("")
            print("")

            for path in sorted_paths:
                print(path)


            #@241224 MARK4OPT_SAVE
            # ************************
            # read "S_month_optimized.csv"
            # trans_month2week2lot_id_list
            # ************************
            if "S_month_optimized.csv" in data_file_list:
            #if "S_month_data.csv" in data_file_list:

                filename = "S_month_optimized.csv"
                in_file_path = os.path.join(directory, filename)


                print("self.lot_size",self.lot_size)

                # 使用例
                #in_file = "S_month_data.csv"

                df_weekly, plan_range, plan_year_st = process_monthly_demand(in_file_path, self.lot_size)

                #df_weekly, plan_range, plan_year_st = trans_month2week2lot_id_list(in_file_path, self.lot_size)


                print("plan_year_st",plan_year_st)
                print("plan_range",plan_range)

                # update plan_year_st plan_range
                self.plan_year_st = plan_year_st  # S_monthで更新
                self.plan_range   = plan_range    # S_monthで更新


                # Update the GUI fields
                self.plan_year_entry.delete(0, tk.END)
                self.plan_year_entry.insert(0, str(self.plan_year_st))
                self.plan_range_entry.delete(0, tk.END)
                self.plan_range_entry.insert(0, str(self.plan_range))


                out_file = "S_iso_week_data_opt.csv"
                out_file_path = os.path.join(directory, out_file)

                df_weekly.to_csv(out_file_path, index=False)

                df_capa_year = make_capa_year_month(in_file_path)

                #@241112 test
                year_st = df_capa_year["year"].min()
                year_end = df_capa_year["year"].max()
                print("year_st, year_end",year_st, year_end)

            else:
                print("error: S_month_optimized.csv is missed")

                pass


            #@241124 ココは、初期のEVAL処理用パラメータ。現在は使用していない
            # planning parameterをNode method(=self.)でセットする。
            # plan_range, lot_counts, cash_in, cash_out用のparameterをセット

            root_node_out_opt.set_plan_range_lot_counts(plan_range, plan_year_st)
            root_node_inbound.set_plan_range_lot_counts(plan_range, plan_year_st)

            # ***************************
            # an image of data
            #
            # for node_val in node_yyyyww_value:
            #   #print( node_val )
            #
            ##['SHA_N', 22.580645161290324, 22.580645161290324, 22.580645161290324, 22.5    80645161290324, 26.22914349276974, 28.96551724137931, 28.96551724137931, 28.    96551724137931, 31.067853170189103, 33.87096774193549, 33.87096774193549, 33    .87096774193549, 33.87096774193549, 30.33333333333333, 30.33333333333333, 30    .33333333333333, 30.33333333333333, 31.247311827956988, 31.612903225806452,

            # node_yyyyww_key [['CAN', 'CAN202401', 'CAN202402', 'CAN202403', 'CAN20240    4', 'CAN202405', 'CAN202406', 'CAN202407', 'CAN202408', 'CAN202409', 'CAN202    410', 'CAN202411', 'CAN202412', 'CAN202413', 'CAN202414', 'CAN202415', 'CAN2    02416', 'CAN202417', 'CAN202418', 'CAN202419',

            # ********************************
            # make_node_psi_dict
            # ********************************
            # 1. treeを生成して、nodes[node_name]辞書で、各nodeのinstanceを操作        する
            # 2. 週次S yyyywwの値valueを月次Sから変換、
            #    週次のlotの数Slotとlot_keyを生成、
            # 3. ロット単位=lot_idとするリストSlot_id_listを生成しながらpsi_list        生成
            # 4. node_psi_dict=[node1: psi_list1,,,]を生成、treeのnode.psi4deman        dに接続する
        
            S_week = []
        
            # *************************************************
            # node_psi辞書を初期セットする
            # initialise node_psi_dict
            # *************************************************
            node_psi_dict = {}  # 変数 node_psi辞書
        
            # ***************************
            # outbound psi_dic
            # ***************************
            node_psi_dict_Ot4Dm = {}  # node_psi辞書Outbound4Demand plan
            node_psi_dict_Ot4Sp = {}  # node_psi辞書Outbound4Supply plan
        
            # coupling psi
            node_psi_dict_Ot4Cl = {}  # node_psi辞書Outbound4Couple plan

            # accume psi
            node_psi_dict_Ot4Ac = {}  # node_psi辞書Outbound4Accume plan
        
            # ***************************
            # inbound psi_dic
            # ***************************
            self.node_psi_dict_In4Dm = {}  # node_psi辞書Inbound4demand plan
            self.node_psi_dict_In4Sp = {}  # node_psi辞書Inbound4supply plan
        
            # coupling psi
            node_psi_dict_In4Cl = {}  # node_psi辞書Inbound4couple plan
        
            # accume psi
            node_psi_dict_In4Ac = {}  # node_psi辞書Inbound4accume plan

            # ***************************
            # rootからtree nodeをpreorder順に検索 node_psi辞書に空リストをセット        する
            # psi_list = [[[] for j in range(4)] for w in range(53 * plan_range)        ]
            # ***************************
            node_psi_dict_Ot4Dm = make_psi_space_dict(
        root_node_out_opt, node_psi_dict_Ot4Dm, plan_range
            )
            node_psi_dict_Ot4Sp = make_psi_space_dict(
                root_node_out_opt, node_psi_dict_Ot4Sp, plan_range
            )
            node_psi_dict_Ot4Cl = make_psi_space_dict(
                root_node_out_opt, node_psi_dict_Ot4Cl, plan_range
            )
            node_psi_dict_Ot4Ac = make_psi_space_dict(
                root_node_out_opt, node_psi_dict_Ot4Ac, plan_range
            )

        


            self.node_psi_dict_In4Dm = make_psi_space_dict(
                root_node_inbound, self.node_psi_dict_In4Dm, plan_range
            )

            self.node_psi_dict_In4Sp = make_psi_space_dict(
                root_node_inbound, self.node_psi_dict_In4Sp, plan_range
            )




            node_psi_dict_In4Cl = make_psi_space_dict(
                root_node_inbound, node_psi_dict_In4Cl, plan_range
            )
            node_psi_dict_In4Ac = make_psi_space_dict(
                root_node_inbound, node_psi_dict_In4Ac, plan_range
            )
        
            # ***********************************
            # set_dict2tree
            # ***********************************
            # rootからtreeをpreorder順に検索
            # node_psi辞書内のpsi_list pointerをNodeのnode objectにsetattr()で接        続
        
            set_dict2tree_psi(root_node_out_opt, "psi4demand", node_psi_dict_Ot4Dm)
            set_dict2tree_psi(root_node_out_opt, "psi4supply", node_psi_dict_Ot4Sp)
            set_dict2tree_psi(root_node_out_opt, "psi4couple", node_psi_dict_Ot4Cl)
            set_dict2tree_psi(root_node_out_opt, "psi4accume", node_psi_dict_Ot4Ac)
        
            set_dict2tree_psi(root_node_inbound, "psi4demand", self.node_psi_dict_In4Dm)
            set_dict2tree_psi(root_node_inbound, "psi4supply", self.node_psi_dict_In4Sp)
            set_dict2tree_psi(root_node_inbound, "psi4couple", node_psi_dict_In4Cl)
            set_dict2tree_psi(root_node_inbound, "psi4accume", node_psi_dict_In4Ac)
        








            #@241224 MARK4OPT_SAVE
            #
            # ココで、root_node_out_optのPSIがsetされ、planning engineに渡る
            #
            # ************************************
            # setting S on PSI
            # ************************************

            # Weekly Lot: CPU:Common Planning UnitをPSI spaceにセットする
            set_df_Slots2psi4demand(root_node_out_opt, df_weekly)



            #@241124 adding for "global market potential"
            # ************************************
            # counting all lots
            # ************************************

            #print("check lots on psi4demand[w][0] ")

            ## count lot on all nodes  from  node.psi4demand[w][0] 
            #lot_num = count_lot_all_nodes(root_node_out_opt)

            # year_st
            # year_end

            # **************************************
            # count_lots_on_S_psi4demand
            # **************************************
            # psi4demand[w][0]の配置されたSのlots数を年別にcountしてlist化


            def count_lots_on_S_psi4demand(node, S_list):
                if node.children == []:
                    for w_psi in node.psi4demand:
                        S_list.append(w_psi[0])
                for child in node.children:
                    count_lots_on_S_psi4demand(child, S_list)
                return S_list

            S_list = []
            year_lots_list4S = []
            S_list = count_lots_on_S_psi4demand(root_node_out_opt, S_list)
            plan_year_st = year_st
            
            #for yyyy in range(plan_year_st, plan_year_st + plan_range + 1):
            for yyyy in range(int(plan_year_st), int(plan_year_st + plan_range + 1)):

                year_lots4S = count_lots_yyyy(S_list, str(yyyy))
                year_lots_list4S.append(year_lots4S)
            
            #@241205 STOP NOT change "global_market_potential" at 2nd loading
            ## 値をインスタンス変数に保存
            #self.global_market_potential = year_lots_list4S[1]  


            print("NOT change #market_potential# at 2nd loading")
            print("self.market_potential", self.market_potential)




        for filename in os.listdir(directory):
            if filename.endswith(".csv"):
                filepath = os.path.join(directory, filename)
                print(f"Loading file: {filename}")
                if "outbound" in filename.lower():
                    self.outbound_data.append(pd.read_csv(filepath))
                elif "inbound" in filename.lower():
                    self.inbound_data.append(pd.read_csv(filepath))
        print("Outbound files loaded.")
        print("Inbound files loaded.")



        #@ STOP optimize processでは初期loadのcost_stracture設定で完了している
        #base_leaf = self.nodes_outbound[self.base_leaf_name]
        #
        #root_price = set_price_leaf2root(base_leaf,self.root_node_out_opt,100)
        #print("root_price", root_price)
        #set_value_chain_outbound(root_price, self.root_node_out_opt)
        

        self.view_nx_matlib()
        self.root.after(1000, self.show_psi_graph)

        #@241222@ STOP RUN
        # パラメータの初期化と更新を呼び出し
        self.initialize_parameters()


        def count_lots_on_S_psi4demand(node, S_list):

            # leaf_node末端市場の判定
            if node.children == []:  # 子nodeがないleaf nodeの場合

                # psi_listからS_listを生成する
                for w_psi in node.psi4demand:  # weeklyのSをS_listに集計

                    S_list.append(w_psi[0])

            else:
                pass

            for child in node.children:
                count_lots_on_S_psi4demand(child, S_list)

            return S_list


        S_list = []
        year_lots_list4S = []

        # treeを生成した直後なので、root_node_out_optが使える
        S_list = count_lots_on_S_psi4demand(root_node_out_opt, S_list)

            # 開始年を取得する
        plan_year_st = year_st  # 開始年のセット in main()要修正
        
        #for yyyy in range(plan_year_st, plan_year_st + plan_range + 1):
        for yyyy in range(int(plan_year_st), int(plan_year_st + plan_range + 1)):
        
            year_lots4S = count_lots_yyyy(S_list, str(yyyy))
        
            year_lots_list4S.append(year_lots4S)
        
            #        # 結果を出力
            #       #print(yyyy, " year carrying lots:", year_lots)
            #
            #    # 結果を出力
            #   #print(" year_lots_list:", year_lots_list)
        
            # an image of sample data
            #
            # 2023  year carrying lots: 0
            # 2024  year carrying lots: 2919
            # 2025  year carrying lots: 2914
            # 2026  year carrying lots: 2986
            # 2027  year carrying lots: 2942
            # 2028  year carrying lots: 2913
            # 2029  year carrying lots: 0
            #
            # year_lots_list4S: [0, 2919, 2914, 2986, 2942, 2913, 0]

            #@241124 CHECK

        #@241205 STOP NOT change "market_potential" at 2nd loading
        ## 値をインスタンス変数に保存
        #self.market_potential = year_lots_list4S[1]  

        #print("year_lots_list4S", year_lots_list4S)

        #self.global_market_potential = year_lots_list4S[1]

        #print("self.global_market_potential", self.global_market_potential)



        for filename in os.listdir(directory):

            if filename.endswith(".csv"):

                filepath = os.path.join(directory, filename)

                print(f"Loading file: {filename}")


                if "outbound" in filename.lower():
                    self.outbound_data.append(pd.read_csv(filepath))
                elif "inbound" in filename.lower():
                    self.inbound_data.append(pd.read_csv(filepath))
        print("Outbound files loaded.")
        print("Inbound files loaded.")
















# *************************
# PSI graph 
# *************************
    def show_psi(self, bound, layer):
        print("making PSI graph data...")

        week_start = 1
        week_end = self.plan_range * 53

        psi_data = []

        if bound not in ["outbound", "inbound"]:
            print("error: outbound or inbound must be defined for PSI layer")
            return

        if layer not in ["demand", "supply"]:
            print("error: demand or supply must be defined for PSI layer")
            return

        def traverse_nodes(node):
            for child in node.children:
                traverse_nodes(child)
            collect_psi_data(node, layer, week_start, week_end, psi_data)

        if bound == "outbound":
            traverse_nodes(self.root_node_outbound)
        else:
            traverse_nodes(self.root_node_inbound)

        cal = Calendar445(
            start_year=self.plan_year_st,
            plan_range=self.plan_range,
            use_13_months=True,
            holiday_country="JP"
        )
        max_year = self.plan_year_st + self.plan_range - 1
        week_to_yymm_all = cal.get_week_labels()
        week_to_yymm = {w: y for w, y in week_to_yymm_all.items() if int(str(y)[:2]) <= max_year % 100}
        month_end_weeks = [w for w in cal.get_month_end_weeks() if w in week_to_yymm]
        holiday_weeks = [w for w in cal.get_holiday_weeks() if w in week_to_yymm]

        print("week_to_yymm", week_to_yymm)

        week_span = week_end - week_start + 1
        fig_width = max(6, min(week_span * 0.08, 9))  # "6"-"18"動的横幅設定（最大幅制限）
        fig, axs = plt.subplots(len(psi_data), 1, figsize=(fig_width, len(psi_data) * 1.5))

        if len(psi_data) == 1:
            axs = [axs]

        for ax, (node_name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S) in zip(axs, psi_data):
            ax2 = ax.twinx()

            ax.bar(line_plot_data_2I.index, line_plot_data_2I.values, color='r', alpha=0.6)
            ax.bar(bar_plot_data_3P.index, bar_plot_data_3P.values, color='g', alpha=0.6)
            ax2.plot(bar_plot_data_0S.index, bar_plot_data_0S.values, color='b')

            ax.set_ylabel('I&P Lots', fontsize=10)
            ax2.set_ylabel('S Lots', fontsize=10)
            ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=10)

            ax.set_xlim(week_start, week_end)
            ax.set_xticks(list(week_to_yymm.keys()))
            ax.set_xticklabels(list(week_to_yymm.values()), rotation=45, fontsize=8)

            for week in month_end_weeks:
                ax.axvspan(week - 0.5, week + 0.5, color='gray', alpha=0.1)

        fig.tight_layout(pad=0.5)

        print("making PSI figure and widget...")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        canvas_psi = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas_psi.draw()
        canvas_psi.get_tk_widget().pack(fill=tk.BOTH, expand=True)


        # PSI描画後のshow_psiの末尾で
        self.scrollable_frame.update_idletasks()
        self.canvas_psi.configure(scrollregion=self.canvas_psi.bbox("all"))

# 描画完了 → サイズ決定 → bbox 更新という順序が必要
#
#update_idletasks() がなければ、まだウィジェットのサイズが未定のまま bbox を取得#しても正しくならない
#
#canvas_psi.get_tk_widget().pack(...) の後で update_idletasks() を呼ぶのがベスト#タイミング

#  Tkinter + Matplotlib の組み合わせでは：
# update_idletasks() の呼び出しタイミング
# scrollregion 設定
# <Configure> イベントの扱い
# …が意外とデリケートなポイント




    def show_psi_BK250702(self, bound, layer): 
        print("making PSI graph data...")

        week_start = 1
        week_end = self.plan_range * 53

        psi_data = []

        if bound not in ["outbound", "inbound"]:
            print("error: outbound or inbound must be defined for PSI layer")
            return

        if layer not in ["demand", "supply"]:
            print("error: demand or supply must be defined for PSI layer")
            return

        def traverse_nodes(node):
            for child in node.children:
                traverse_nodes(child)
            collect_psi_data(node, layer, week_start, week_end, psi_data)

        if bound == "outbound":
            traverse_nodes(self.root_node_outbound)
        else:
            traverse_nodes(self.root_node_inbound)

        # Calendar445で軸情報・祝日情報を取得（13期・日本の祝日モードON）
        # カレンダー設定とフィルタ処理
        cal = Calendar445(
            start_year=self.plan_year_st,
            plan_range=self.plan_range,
            use_13_months=True,
            holiday_country="JP"
        )
        week_start = 1
        week_end = self.plan_range * 53 - 1  # 余分な年を除く
        week_to_yymm = {w: y for w, y in cal.get_week_labels().items() if week_start <= w <= week_end}
        month_end_weeks = [w for w in cal.get_month_end_weeks() if w <= week_end]
        holiday_weeks = [w for w in cal.get_holiday_weeks() if w <= week_end]

        print("week_to_yymm", week_to_yymm)


        #@250703 STOP
        #cal = Calendar445(
        #    start_year=self.plan_year_st,
        #    plan_range=self.plan_range,
        #    use_13_months=True,
        #    holiday_country="JP"
        #)
        #week_to_yymm = cal.get_week_labels()
        #month_end_weeks = cal.get_month_end_weeks()
        #holiday_weeks = cal.get_holiday_weeks()






        fig, axs = plt.subplots(len(psi_data), 1, figsize=(5, len(psi_data) * 1))  # 高さ控えめ

        if len(psi_data) == 1:
            axs = [axs]

        for ax, (node_name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S) in zip(axs, psi_data):
            ax2 = ax.twinx()

            ax.bar(line_plot_data_2I.index, line_plot_data_2I.values, color='r', alpha=0.6)
            ax.bar(bar_plot_data_3P.index, bar_plot_data_3P.values, color='g', alpha=0.6)
            ax2.plot(bar_plot_data_0S.index, bar_plot_data_0S.values, color='b')

            ax.set_ylabel('I&P Lots', fontsize=8)
            ax2.set_ylabel('S Lots', fontsize=8)
            ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=8)

            # 共通時間軸設定
            ax.set_xlim(week_start, week_end)
            ax.set_xticks(list(week_to_yymm.keys()))
            ax.set_xticklabels(list(week_to_yymm.values()), rotation=45, fontsize=6)

            # 月末週のグレーアウト
            for week in month_end_weeks:
                ax.axvspan(week - 0.5, week + 0.5, color='gray', alpha=0.1)

            # 祝日週の赤帯表示
            for week in holiday_weeks:
                ax.axvspan(week - 0.5, week + 0.5, color='red', alpha=0.05)

        fig.tight_layout(pad=0.5)

        print("making PSI figure and widget...")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        canvas_psi = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas_psi.draw()
        canvas_psi.get_tk_widget().pack(fill=tk.BOTH, expand=True)



    def show_psi_OLD2507032131(self, bound, layer):
        print("making PSI graph data...")

        week_start = 1
        week_end = self.plan_range * 53

        psi_data = []

        if bound not in ["outbound", "inbound"]:
            print("error: outbound or inbound must be defined for PSI layer")
            return

        if layer not in ["demand", "supply"]:
            print("error: demand or supply must be defined for PSI layer")
            return

        def traverse_nodes(node):
            for child in node.children:
                traverse_nodes(child)
            collect_psi_data(node, layer, week_start, week_end, psi_data)

        if bound == "outbound":
            traverse_nodes(self.root_node_outbound)
        else:
            traverse_nodes(self.root_node_inbound)

        cal = Calendar445(
            start_year=self.plan_year_st,
            plan_range=self.plan_range,
            use_13_months=True,
            holiday_country="JP"
        )
        max_year = self.plan_year_st + self.plan_range - 1
        week_to_yymm_all = cal.get_week_labels()
        week_to_yymm = {w: y for w, y in week_to_yymm_all.items() if int(str(y)[:2]) <= max_year % 100}
        month_end_weeks = [w for w in cal.get_month_end_weeks() if w in week_to_yymm]
        holiday_weeks = [w for w in cal.get_holiday_weeks() if w in week_to_yymm]

        print("week_to_yymm", week_to_yymm)

        week_span = week_end - week_start + 1
        fig_width = max(6, min(week_span * 0.08, 6))  # 6-18で動的横幅設定（最大幅制限）
        #fig_width = max(6, min(week_span * 0.08, 18))  # 6-18で動的横幅設定（最大幅制限）
        fig, axs = plt.subplots(len(psi_data), 1, figsize=(fig_width, len(psi_data) * 1.5))

        if len(psi_data) == 1:
            axs = [axs]

        for ax, (node_name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S) in zip(axs, psi_data):
            ax2 = ax.twinx()

            ax.bar(line_plot_data_2I.index, line_plot_data_2I.values, color='r', alpha=0.6)
            ax.bar(bar_plot_data_3P.index, bar_plot_data_3P.values, color='g', alpha=0.6)
            ax2.plot(bar_plot_data_0S.index, bar_plot_data_0S.values, color='b')

            ax.set_ylabel('I&P Lots', fontsize=10)
            ax2.set_ylabel('S Lots', fontsize=10)
            ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=10)

            ax.set_xlim(week_start, week_end)
            ax.set_xticks(list(week_to_yymm.keys()))
            ax.set_xticklabels(list(week_to_yymm.values()), rotation=45, fontsize=8)

            for week in month_end_weeks:
                ax.axvspan(week - 0.5, week + 0.5, color='gray', alpha=0.1)

        fig.tight_layout(pad=0.5)

        print("making PSI figure and widget...")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        canvas_psi = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas_psi.draw()
        canvas_psi.get_tk_widget().pack(fill=tk.BOTH, expand=True)



    def show_psi_OLD2507032023(self, bound, layer):
        print("making PSI graph data...")

        week_start = 1
        week_end = self.plan_range * 53

        psi_data = []

        if bound not in ["outbound", "inbound"]:
            print("error: outbound or inbound must be defined for PSI layer")
            return

        if layer not in ["demand", "supply"]:
            print("error: demand or supply must be defined for PSI layer")
            return

        def traverse_nodes(node):
            for child in node.children:
                traverse_nodes(child)
            collect_psi_data(node, layer, week_start, week_end, psi_data)

        if bound == "outbound":
            traverse_nodes(self.root_node_outbound)
        else:
            traverse_nodes(self.root_node_inbound)

        cal = Calendar445(
            start_year=self.plan_year_st,
            plan_range=self.plan_range,
            use_13_months=True,
            holiday_country="JP"
        )
        max_year = self.plan_year_st + self.plan_range - 1
        week_to_yymm_all = cal.get_week_labels()
        week_to_yymm = {w: y for w, y in week_to_yymm_all.items() if int(str(y)[:2]) <= max_year % 100}
        month_end_weeks = [w for w in cal.get_month_end_weeks() if w in week_to_yymm]
        holiday_weeks = [w for w in cal.get_holiday_weeks() if w in week_to_yymm]

        print("week_to_yymm", week_to_yymm)

        week_span = week_end - week_start + 1
        fig_width = max(6, week_span * 0.08)  # 動的横幅設定
        fig, axs = plt.subplots(len(psi_data), 1, figsize=(fig_width, len(psi_data) * 1.5))

        if len(psi_data) == 1:
            axs = [axs]

        for ax, (node_name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S) in zip(axs, psi_data):
            ax2 = ax.twinx()

            ax.bar(line_plot_data_2I.index, line_plot_data_2I.values, color='r', alpha=0.6)
            ax.bar(bar_plot_data_3P.index, bar_plot_data_3P.values, color='g', alpha=0.6)
            ax2.plot(bar_plot_data_0S.index, bar_plot_data_0S.values, color='b')

            ax.set_ylabel('I&P Lots', fontsize=10)
            ax2.set_ylabel('S Lots', fontsize=10)
            ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=10)

            ax.set_xlim(week_start, week_end)
            ax.set_xticks(list(week_to_yymm.keys()))
            ax.set_xticklabels(list(week_to_yymm.values()), rotation=45, fontsize=8)

            for week in month_end_weeks:
                ax.axvspan(week - 0.5, week + 0.5, color='gray', alpha=0.1)

        fig.tight_layout(pad=0.5)

        print("making PSI figure and widget...")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        canvas_psi = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas_psi.draw()
        canvas_psi.get_tk_widget().pack(fill=tk.BOTH, expand=True)




    def show_psi_OLD2507031616(self, bound, layer): # Calendar445
        print("making PSI graph data...")

        week_start = 1
        week_end = self.plan_range * 53 - 1  # 修正：1年分余分を除く

        #week_end = self.plan_range * 53
        #week_end = ( self.plan_range - 1 ) * 53



        psi_data = []

        if bound not in ["outbound", "inbound"]:
            print("error: outbound or inbound must be defined for PSI layer")
            return

        if layer not in ["demand", "supply"]:
            print("error: demand or supply must be defined for PSI layer")
            return

        def traverse_nodes(node):
            for child in node.children:
                traverse_nodes(child)
            collect_psi_data(node, layer, week_start, week_end, psi_data)

        if bound == "outbound":
            traverse_nodes(self.root_node_outbound)
        else:
            traverse_nodes(self.root_node_inbound)




        #@250703 STOP
        ## Calendar445で軸情報・祝日情報を取得（13期・日本の祝日モードON）
        ## カレンダー設定とフィルタ処理
        #cal = Calendar445(
        #    start_year=self.plan_year_st,
        #    plan_range=self.plan_range,
        #    use_13_months=True,
        #    holiday_country="JP"
        #)
        #week_start = 1
        #week_end = self.plan_range * 53 - 1  # 余分な年を除く
        #week_to_yymm = {w: y for w, y in cal.get_week_labels().items() if week_start <= w <= week_end}
        #month_end_weeks = [w for w in cal.get_month_end_weeks() if w <= week_end]
        #holiday_weeks = [w for w in cal.get_holiday_weeks() if w <= week_end]





        # カレンダー設定とフィルタ処理（週番号ではなく yymm に基づいて正確に制限）
        cal = Calendar445(
            start_year=self.plan_year_st,
            plan_range=self.plan_range,
            use_13_months=True,
            holiday_country="JP"
        )
        week_start = 1
        week_end = self.plan_range * 53
        max_year = self.plan_year_st + self.plan_range - 1
        week_to_yymm_all = cal.get_week_labels()
        week_to_yymm = {w: y for w, y in week_to_yymm_all.items() if int(str(y)[:2]) <= max_year % 100}
        month_end_weeks = [w for w in cal.get_month_end_weeks() if w in week_to_yymm]
        holiday_weeks = [w for w in cal.get_holiday_weeks() if w in week_to_yymm]




        print("week_to_yymm", week_to_yymm)







        #@250703 STOP
        # 4-4-5カレンダーの横軸ラベルと月末週を取得
        #cal = Calendar445(start_year=self.plan_year_st, plan_range=self.plan_range)
        #week_to_yymm = cal.get_week_labels()
        #month_end_weeks = cal.get_month_end_weeks()



        #@250703 STOP
        #cal = Calendar445(
        #    start_year=self.plan_year_st,
        #    plan_range=self.plan_range,
        #    use_13_months=True,
        #    holiday_country="JP"
        #)
        #week_to_yymm = cal.get_week_labels()
        #month_end_weeks = cal.get_month_end_weeks()
        #holiday_weeks = cal.get_holiday_weeks()





        fig, axs = plt.subplots(len(psi_data), 1, figsize=(6, len(psi_data) * 1.5))  

        #fig, axs = plt.subplots(len(psi_data), 1, figsize=(5, len(psi_data) * 1))  # 高さ控えめ

        # グラフ全体の横幅を 8インチ、各サブプロットの高さを 1.5インチ 
        # にしたい場合、次のように変更します。
        # fig, axs = plt.subplots(len(psi_data), 1, figsize=(8, len(psi_data) * 1.5))



        if len(psi_data) == 1:
            axs = [axs]

        for ax, (node_name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S) in zip(axs, psi_data):
            ax2 = ax.twinx()

            ax.bar(line_plot_data_2I.index, line_plot_data_2I.values, color='r', alpha=0.6)
            ax.bar(bar_plot_data_3P.index, bar_plot_data_3P.values, color='g', alpha=0.6)
            ax2.plot(bar_plot_data_0S.index, bar_plot_data_0S.values, color='b')

            ax.set_ylabel('I&P Lots', fontsize=10) #@250702 fantsize 8=>10
            ax2.set_ylabel('S Lots', fontsize=10)
            ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=10)

            # 共通時間軸設定
            ax.set_xlim(week_start, week_end)
            ax.set_xticks(list(week_to_yymm.keys()))
            ax.set_xticklabels(list(week_to_yymm.values()), rotation=45, fontsize=8)

            # 月末週のグレーアウト
            for week in month_end_weeks:
                ax.axvspan(week - 0.5, week + 0.5, color='gray', alpha=0.1)

        fig.tight_layout(pad=0.5)

        print("making PSI figure and widget...")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        canvas_psi = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas_psi.draw()
        canvas_psi.get_tk_widget().pack(fill=tk.BOTH, expand=True)




    def show_psi_OLD(self, bound, layer):
        print("making PSI graph data...")
    
        week_start = 1
        week_end = self.plan_range * 53
    
        psi_data = []
    
        if bound not in ["outbound", "inbound"]:
            print("error: outbound or inbound must be defined for PSI layer")
            return
    
        if layer not in ["demand", "supply"]:
            print("error: demand or supply must be defined for PSI layer")
            return
    
        def traverse_nodes(node):
            for child in node.children:
                traverse_nodes(child)
            collect_psi_data(node, layer, week_start, week_end, psi_data)
    
        if bound == "outbound":
            traverse_nodes(self.root_node_outbound)
        else:
            traverse_nodes(self.root_node_inbound)
    
        fig, axs = plt.subplots(len(psi_data), 1, figsize=(5, len(psi_data) * 1))  # figsizeの高さをさらに短く設定
    
        if len(psi_data) == 1:
            axs = [axs]

        for ax, (node_name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S) in zip(axs, psi_data):
            ax2 = ax.twinx()
    
            ax.bar(line_plot_data_2I.index, line_plot_data_2I.values, color='r', alpha=0.6)
            ax.bar(bar_plot_data_3P.index, bar_plot_data_3P.values, color='g', alpha=0.6)
            ax2.plot(bar_plot_data_0S.index, bar_plot_data_0S.values, color='b')
    
            ax.set_ylabel('I&P Lots', fontsize=10) 
            ax2.set_ylabel('S Lots', fontsize=10)
            ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=10)
    
        fig.tight_layout(pad=0.5)
    
        print("making PSI figure and widget...")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
    
        canvas_psi = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas_psi.draw()
        canvas_psi.get_tk_widget().pack(fill=tk.BOTH, expand=True)





    def show_psi_graph(self):
        print("making PSI graph data...")

        week_start = 1
        week_end = self.plan_range * 53

        psi_data = []

        def traverse_nodes(node):
            for child in node.children:
                traverse_nodes(child)
            collect_psi_data(node, "demand", week_start, week_end, psi_data)

        # ***************************
        # ROOT HANDLE
        # ***************************
        traverse_nodes(self.root_node_outbound)

        fig, axs = plt.subplots(len(psi_data), 1, figsize=(5, len(psi_data) * 1))  # figsizeの高さをさらに短く設定

        if len(psi_data) == 1:
            axs = [axs]

        for ax, (node_name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S) in zip(axs, psi_data):
            ax2 = ax.twinx()

            ax.bar(line_plot_data_2I.index, line_plot_data_2I.values, color='r', alpha=0.6)
            ax.bar(bar_plot_data_3P.index, bar_plot_data_3P.values, color='g', alpha=0.6)
            ax2.plot(bar_plot_data_0S.index, bar_plot_data_0S.values, color='b')

            ax.set_ylabel('I&P Lots', fontsize=8)
            ax2.set_ylabel('S Lots', fontsize=8)
            ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=8)

            # Y軸の整数設定
            ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        fig.tight_layout(pad=0.5)

        print("making PSI figure and widget...")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        canvas_psi = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas_psi.draw()
        canvas_psi.get_tk_widget().pack(fill=tk.BOTH, expand=True)




    #@241225 marked revenueとprofitは、node classにインスタンスあり
    def show_psi_graph4opt(self):
        print("making PSI graph data...")

        week_start = 1
        week_end = self.plan_range * 53

        psi_data = []

        nodes_outbound = self.nodes_outbound  # node辞書{}

        def traverse_nodes(node_opt):
            for child in node_opt.children:
                print("show_psi_graph4opt child.name", child.name)
                traverse_nodes(child)
            node_out = nodes_outbound[node_opt.name]
            collect_psi_data_opt(node_opt, node_out, "supply", week_start, week_end, psi_data)

        # ***************************
        # change ROOT HANDLE
        # ***************************
        traverse_nodes(self.root_node_out_opt)

        fig, axs = plt.subplots(len(psi_data), 1, figsize=(5, len(psi_data) * 1))  # figsizeの高さをさらに短く設定

        if len(psi_data) == 1:
            axs = [axs]

        for ax, (node_name, revenue, profit, profit_ratio, line_plot_data_2I, bar_plot_data_3P, bar_plot_data_0S) in zip(axs, psi_data):
            ax2 = ax.twinx()

            ax.bar(line_plot_data_2I.index, line_plot_data_2I.values, color='r', alpha=0.6)
            ax.bar(bar_plot_data_3P.index, bar_plot_data_3P.values, color='g', alpha=0.6)
            ax2.plot(bar_plot_data_0S.index, bar_plot_data_0S.values, color='b')

            ax.set_ylabel('I&P Lots', fontsize=8)
            ax2.set_ylabel('S Lots', fontsize=8)
            ax.set_title(f'Node: {node_name} | REVENUE: {revenue:,} | PROFIT: {profit:,} | PROFIT_RATIO: {profit_ratio}%', fontsize=8)

            # Y軸の整数設定
            ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
            ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        fig.tight_layout(pad=0.5)

        print("making PSI figure and widget...")

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        canvas_psi = FigureCanvasTkAgg(fig, master=self.scrollable_frame)
        canvas_psi.draw()
        canvas_psi.get_tk_widget().pack(fill=tk.BOTH, expand=True)





