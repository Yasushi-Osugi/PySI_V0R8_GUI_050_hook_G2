# pysi/app/entry_gui.py

# starter
# python -m pysi.app.entry_gui

#@251025 start and check 

# python -m pysi.app.entry_gui

#Scenario Root: examples/scenarios
#Scenario: v0r7_rice
#Plugins Dir: pysi/plugins（またはプロジェクトの ./plugins でも可）
#Weeks: 3 → Run

#期待ログ：
#[INFO] start → run_id=... start
#Hookのプラグイン読み込み（重複表示がある場合は他所の autoload 併用を整理）
#done

#期待成果物：
#examples/scenarios/v0r7_rice/_out/series.csv / kpi.csv（report_minimalが出力）


import tkinter as tk
from tkinter import ttk, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading, queue, os

from pysi.app.run_once import run_once
from pysi.core.hooks.core import HookBus, set_global
from pysi.io_adapters.csv_adapter import CSVAdapter

class GuiLogger:
    def __init__(self, text_widget):
        self.text = text_widget
    def info(self, msg): self._write(f"[INFO] {msg}\n")
    def warn(self, msg): self._write(f"[WARN] {msg}\n")
    def error(self, msg): self._write(f"[ERROR] {msg}\n")
    def exception(self, msg): self._write(f"[ERROR] {msg}\n")
    def _write(self, s):
        self.text.after(0, lambda: (self.text.insert(tk.END, s), self.text.see(tk.END)))

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PySI GUI (V0R8 CSV/Hook)")
        self.geometry("980x700")

        frm = ttk.Frame(self); frm.pack(fill="x", padx=8, pady=6)
        self.var_root    = tk.StringVar()
        self.var_scn     = tk.StringVar()
        self.var_plugins = tk.StringVar(value="./plugins")
        self.var_weeks   = tk.IntVar(value=3)
        self.var_year    = tk.IntVar(value=2025)
        self.var_week    = tk.IntVar(value=1)

        ttk.Label(frm,text="Scenario Root").grid(row=0,column=0,sticky="w")
        ent_root = ttk.Entry(frm,textvariable=self.var_root,width=60); ent_root.grid(row=0,column=1,sticky="we")
        ttk.Button(frm,text="Browse",command=self.pick_root).grid(row=0,column=2)

        ttk.Label(frm,text="Scenario").grid(row=1,column=0,sticky="w")
        self.cmb_scn = ttk.Combobox(frm,textvariable=self.var_scn,width=40,values=[])
        self.cmb_scn.grid(row=1,column=1,sticky="w")
        ttk.Button(frm,text="Scan",command=self.scan_scenarios).grid(row=1,column=2)

        ttk.Label(frm,text="Plugins Dir").grid(row=2,column=0,sticky="w")
        ent_plg = ttk.Entry(frm,textvariable=self.var_plugins,width=60); ent_plg.grid(row=2,column=1,sticky="we")
        ttk.Button(frm,text="Browse",command=self.pick_plugins).grid(row=2,column=2)

        ttk.Label(frm,text="Weeks").grid(row=3,column=0,sticky="w")
        ttk.Entry(frm,textvariable=self.var_weeks,width=8).grid(row=3,column=1,sticky="w")
        ttk.Label(frm,text="ISO Year/Week").grid(row=3,column=1,sticky="e")
        ttk.Entry(frm,textvariable=self.var_year,width=8).grid(row=3,column=1,sticky="e",padx=(0,90))
        ttk.Entry(frm,textvariable=self.var_week,width=6).grid(row=3,column=1,sticky="e",padx=(0,10))
        ttk.Button(frm,text="Run",command=self.run_pipeline).grid(row=3,column=2,sticky="e")

        paned = ttk.Panedwindow(self,orient="horizontal"); paned.pack(fill="both",expand=True,padx=8,pady=6)
        left = ttk.Frame(paned); right = ttk.Frame(paned); paned.add(left,weight=1); paned.add(right,weight=1)
        self.txt = tk.Text(left,wrap="word"); self.txt.pack(fill="both",expand=True)
        self.logger = GuiLogger(self.txt)

        fig = Figure(figsize=(5,4), dpi=100)
        self.ax  = fig.add_subplot(111)
        self.ax.set_title("PSI Preview")
        self.canvas = FigureCanvasTkAgg(fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both",expand=True)

        self.plot_queue = queue.Queue()
        self.after(200, self._drain_plots)

    def pick_root(self):
        d = filedialog.askdirectory()
        if d: self.var_root.set(d)

    def pick_plugins(self):
        d = filedialog.askdirectory()
        if d: self.var_plugins.set(d)

    def scan_scenarios(self):
        root = self.var_root.get() or "."
        if not os.path.isdir(root): return
        names = [n for n in os.listdir(root) if os.path.isdir(os.path.join(root,n))]
        self.cmb_scn["values"] = names
        if names: self.var_scn.set(names[0])

    def run_pipeline(self):
        cfg = {
            "root": self.var_root.get(),
            "scenario_id": self.var_scn.get(),
            "plugins_dir": self.var_plugins.get(),
            "out_dir": os.path.join(self.var_root.get(), "_out"),
            "calendar": {
                "weeks": int(self.var_weeks.get()),
                "iso_year_start": int(self.var_year.get()),
                "iso_week_start": int(self.var_week.get()),
            },
            "meta": {
                "csv_layout": "v0r7",
                "preferred_root": "outbound",
                "root_dir": self.var_root.get(),
            },
        }
        threading.Thread(target=self._run_bg, args=(cfg,), daemon=True).start()

    def _run_bg(self, cfg):
        try:
            self.logger.info("start")
            bus = HookBus(logger=self.logger); set_global(bus)
            io  = CSVAdapter(root=cfg["root"], schema_cfg=cfg.get("schema_cfg"), logger=self.logger)

            run_once(cfg, bus=bus, io=io, logger=self.logger)

            self.plot_queue.put(([0,1,2,3], [10,20,15,25]))
            self.logger.info("done")
            
        except Exception as e:
            self.logger.error(str(e))

    def _drain_plots(self):
        try:
            while True:
                xs, ys = self.plot_queue.get_nowait()
                self.ax.clear(); self.ax.plot(xs, ys); self.canvas.draw()
        except queue.Empty:
            pass
        self.after(200, self._drain_plots)

if __name__ == "__main__":
    App().mainloop()
