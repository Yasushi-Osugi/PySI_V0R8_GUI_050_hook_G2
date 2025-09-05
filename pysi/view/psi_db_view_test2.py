# pysi/view/psi_db_view_test2.py
from __future__ import annotations
import sqlite3, json, sys
from collections import deque
from pathlib import Path
from typing import Dict, Tuple, List

# --- add project root to sys.path (…/PySI_V0R8_SQL_010) ---
ROOT = Path(__file__).resolve().parents[2]  # …/pysi/view/.. (= project root)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
from pysi.network.node_base import Node  # 既存の Node

# --- DB -> ツリー復元 ---
def load_tree_from_db(db_path: str) -> dict[str, Node]:
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        nodes: dict[str, Node] = {}

        # ノード属性
        for r in con.execute("SELECT * FROM node"):
            n = nodes.setdefault(r["node_name"], Node(r["node_name"]))
            try:
                n.leadtime = int(r["leadtime"] or 0)
            except Exception:
                n.leadtime = 0
            try:
                n.SS_days  = int(r["ss_days"] or 0)
            except Exception:
                n.SS_days = 0
            lv = r["long_vacation_weeks"]
            try:
                n.long_vacation_weeks = json.loads(lv) if lv else []
            except Exception:
                n.long_vacation_weeks = []

        # 親子リンク（Node.add_child が無い環境でも動くようにフォールバック）
        def _link(p: Node, c: Node):
            if hasattr(p, "add_child") and callable(getattr(p, "add_child")):
                p.add_child(c)
            else:
                if not hasattr(p, "children"): p.children = []
                if not hasattr(c, "parent"):   c.parent = None
                p.children.append(c)
                c.parent = p

        for r in con.execute("SELECT node_name, parent_name FROM node"):
            child = nodes[r["node_name"]]
            parent_name = r["parent_name"]
            if parent_name and parent_name in nodes:
                _link(nodes[parent_name], child)

        # ルート（親を持たない）
        has_parent = {
            r["node_name"] for r in con.execute(
                "SELECT node_name FROM node WHERE parent_name IS NOT NULL"
            )
        }
        roots = {name: n for name, n in nodes.items() if name not in has_parent}
        return roots

# --- 位置計算（シンプル tidy tree）---
def _assign_positions(n: Node, x: int, y_cursor: List[int], pos: Dict[Node, Tuple[float,float]]) -> float:
    if not getattr(n, "children", []):
        y = y_cursor[0]
        pos[n] = (x, y)
        y_cursor[0] += 1
        return y
    ys = []
    for c in n.children:
        ys.append(_assign_positions(c, x+1, y_cursor, pos))
    y = sum(ys)/len(ys)
    pos[n] = (x, y)
    return y

def compute_positions(root: Node) -> Dict[Node, Tuple[float,float]]:
    pos: Dict[Node, Tuple[float,float]] = {}
    _assign_positions(root, x=0, y_cursor=[0], pos=pos)
    ys = [p[1] for p in pos.values()] or [0, 1]
    ymin, ymax = min(ys), max(ys)
    scale = (ymax - ymin) or 1.0
    return {n: (x, (y - ymin)/scale) for n, (x, y) in pos.items()}

# --- BFSダンプ ---
def print_bfs(root: Node):
    q = deque([(root, 0)])
    seen = set()
    while q:
        n, d = q.popleft()
        if id(n) in seen: 
            continue
        seen.add(id(n))
        print(f"[BFS d={d}] {n.name} -> {[c.name for c in getattr(n,'children',[])]}")
        for c in getattr(n, "children", []):
            q.append((c, d+1))

# --- 描画 ---
def draw_tree_matplotlib(root: Node, figsize=(11, 6), title: str | None = None):
    pos = compute_positions(root)
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_axis_off()
    ax.set_title(title or f"Supply Chain Tree: {root.name}", fontsize=12)

    # edges
    for parent, (x, y) in pos.items():
        for child in getattr(parent, "children", []) or []:
            (xc, yc) = pos[child]
            ax.plot([x, xc], [y, yc], color="#999", linewidth=1.4, zorder=1)

    # nodes
    for n, (x, y) in pos.items():
        is_leaf = not getattr(n, "children", [])
        color = "#1f77b4" if not is_leaf else "#2ca02c"
        ax.scatter([x], [y], s=260, color=color, zorder=2)
        ax.text(x, y, n.name, ha="center", va="center", color="white",
                fontsize=9, fontweight="bold", zorder=3)

    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    if xs and ys:
        ax.set_xlim(min(xs)-0.6, max(xs)+0.6)
        ax.set_ylim(min(ys)-0.05, max(ys)+0.05)

    plt.tight_layout()
    plt.show()

# --- まとめて実行 ---
def psi_db_view_test(db_path: str):
    roots = load_tree_from_db(db_path)
    if not roots:
        print("[WARN] no roots found.")
        return
    for root_name, root in roots.items():
        print(f"[INFO] root: {root_name}")
        print_bfs(root)
        draw_tree_matplotlib(root, title=f"Root={root_name}")

if __name__ == "__main__":
    # 1) ルートからモ
