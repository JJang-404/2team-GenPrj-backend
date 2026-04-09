@echo off
robocopy "D:\project\genPrj\2team-GenPrj-backend" "W:\project\2team-GenPrj-backend" /MIR /MT:8 /R:2 /W:2 /XD .web .venv __pycache__ .states  .github .git mlruns .vscode data .streamlit /XF *.pyc
