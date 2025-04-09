set -e
source env/bin/activate
exec python3 mybustimesAPI/manage.py runserver 0.0.0.0:8000