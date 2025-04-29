@echo on
call env\Scripts\activate
python mybustimesAPI/manage.py makemigrations mybustimes
python mybustimesAPI/manage.py makemigrations routes
python mybustimesAPI/manage.py makemigrations gameData
python mybustimesAPI/manage.py makemigrations admin_dash
python mybustimesAPI/manage.py migrate
rem python mybustimesAPI/manage.py loaddata initial_data.json
