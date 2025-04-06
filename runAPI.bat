@echo on
call env\Scripts\activate
start /B python mybustimesAPI\manage.py runserver
timeout /t 5 /nobreak >nul
start /B node index.js