# --- スクリプト開始 ---

# 1. 最適な .gitignore を書き出す
@"
# SQLite / Reports / Cache
var/
report/
*.sqlite

# Python キャッシュ
__pycache__/
*.pyc
*.pyo

# Excel / CSV / 作業ファイル / バックアップ
*.xlsx
*_BK*.csv
*_BK*.py
*_work.*
*WORK.*
*work.*
backup/
*_optimized.*
*~$*

# ワーク用データ
data/
_data_parameters/
"@ | Out-File -Encoding utf8 .gitignore

# 2. すでにGitで追跡されているファイルを解除
git rm -r --cached .

# 3. 改めて.gitignoreに従ってステージング
git add .

# 4. コミット（履歴にクリーンな状態を記録）
git commit -m "Clean commit with updated .gitignore"

# --- スクリプト終了 ---
