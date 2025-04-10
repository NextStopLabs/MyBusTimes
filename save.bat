@echo on
call env\Scripts\activate
python mybustimesAPI/manage.py dumpdata mybustimes.region mybustimes.theme mybustimes.featureToggle --indent 2 > initial_data.json