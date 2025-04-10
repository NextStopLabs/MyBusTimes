@echo on
call env\Scripts\activate
python mybustimesAPI/manage.py makemigrations mybustimes
python mybustimesAPI/manage.py migrate
python mybustimesAPI/manage.py loaddata fixtures/initial_data.json
