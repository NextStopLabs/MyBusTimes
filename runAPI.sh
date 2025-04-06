set -e
source env/bin/activate
nohup python3 mybustimesAPI/manage.py runserver &
sleep 5
nohup node index.js &