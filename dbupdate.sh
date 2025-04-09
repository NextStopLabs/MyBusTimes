set -e
python3 mybustimesAPI/manage.py makemigrations mybustimes
python3 mybustimesAPI/manage.py migrate