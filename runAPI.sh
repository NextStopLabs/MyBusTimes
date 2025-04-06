set -e
source env/Scripts/activate
nohup python mybustimesAPI/manage.py runserver &
sleep 5
nohup node index.js &