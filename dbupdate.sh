set -e
python mybustimesAPI/manage.py makemigrations mybustimes
python mybustimesAPI/manage.py migrate
bash runAPI.bat