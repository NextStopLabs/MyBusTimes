@echo on
call env\Scripts\activate
python mybustimesAPI/manage.py makemigrations mybustimes
python mybustimesAPI/manage.py migrate
call runAPI.bat