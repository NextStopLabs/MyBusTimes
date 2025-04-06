set -e
source env/bin/activate
python3 mybustimesAPI/manage.py runserver &
sleep 5
node index.js