@echo on
python -m venv env
call env\Scripts\activate
pip install --upgrade pip
pip install django djangorestframework django-cors-headers djangorestframework-simplejwt django-filter Pillow
npm install
python mybustimesAPI/manage.py makemigrations mybustimes
python mybustimesAPI/manage.py migrate
python mybustimesAPI/manage.py loaddata fixtures/initial_data.json