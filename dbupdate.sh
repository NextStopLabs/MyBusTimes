set -e
source env/bin/activate
python3 mybustimesAPI/manage.py makemigrations mybustimes
python3 mybustimesAPI/manage.py migrate
python3 mybustimesAPI/manage.py loaddata initial_data.json
