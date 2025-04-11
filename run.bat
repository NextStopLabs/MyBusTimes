@echo on
call env\Scripts\activate
start cmd /k "python mybustimesAPI\manage.py runserver"
start cmd /k "node index.js"