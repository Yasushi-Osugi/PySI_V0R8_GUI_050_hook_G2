git init
echo "var/*.sqlite`n__pycache__/`n*.pyc`nreport/*" >> .gitignore
git add .
git commit -m "PSI Planner baseline"