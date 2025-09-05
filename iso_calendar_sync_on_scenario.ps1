python - << 'PY'
import sqlite3
from pysi.db.calendar_iso import ensure_calendar_iso
con = sqlite3.connect(r"var/psi.sqlite")
row = con.execute("SELECT plan_year_st, plan_range FROM scenario WHERE name=?",
                  ('Baseline',)).fetchone()
if not row:
    raise SystemExit("scenario 'Baseline' がまだありません（まずETLを流してください）")
y0, pr = map(int, row)
n = ensure_calendar_iso(con, y0, pr)
print(f"calendar_iso synced: weeks={n}, plan_year_st={y0}, plan_range={pr}")
con.close()
PY