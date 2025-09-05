


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



# ****************************
# PSI planning demand
# ****************************
def calc_all_psi2i4demand(node):

    node.calcPS2I4demand()

    for child in node.children:

        calc_all_psi2i4demand(child)




