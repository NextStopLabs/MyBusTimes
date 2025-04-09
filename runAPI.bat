@echo on
call env\Scripts\activate
start cmd /k "python mybustimesAPI\manage.py runserver"
timeout /t 5 /nobreak >nul
start cmd /k "node index.js"
