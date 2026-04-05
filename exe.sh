
#ps -ef | grep python
#source ./.venv/bin/activate
#nohup bash exe.sh > server.log 2>&1 &
export BACKEND_PORT=8000
python -m  app.main
python