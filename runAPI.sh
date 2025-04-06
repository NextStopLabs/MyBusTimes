set -e
source env/bin/activate
nohup python mybustimesAPI/manage.py runserver &
sleep 5
nohup node index.js &