#main.py

# main.py
from pysi.utils.config import Config
import tkinter as tk

USE_SQL_BACKEND = True
DB_PATH = r"C:\Users\ohsug\PySI_V0R8_SQL_010\data\pysi.sqlite3"

def build_env():
    if USE_SQL_BACKEND:
        from pysi.io.sql_planenv import SqlPlanEnv
        return SqlPlanEnv(DB_PATH)
    else:
        from pysi.psi_planner_mvp.plan_env_main import PlanEnv
        env = PlanEnv(Config())
        env.load_data_files()  # CSV読み込み
        return env

def main():
    config = Config()
    psi_env = build_env()

    psi_env.reload() # DB reload

    from pysi.gui.app import PSIPlannerApp
    root = tk.Tk()
    app = PSIPlannerApp(root, config, psi_env=psi_env)  # ★ 依存注入
    root.mainloop()

if __name__ == "__main__":
    main()
