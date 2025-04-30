set -e
source env/bin/activate
python3 mybustimesAPI/manage.py makemigrations mybustimes
python3 mybustimesAPI/manage.py makemigrations routes
python3 mybustimesAPI/manage.py makemigrations gameData
python3 mybustimesAPI/manage.py makemigrations admin_dash
python3 mybustimesAPI/manage.py migrate
python3 mybustimesAPI/manage.py loaddata initial_data.json
