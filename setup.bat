@echo on
python -m venv env
call env\Scripts\activate
pip install --upgrade pip
pip install django djangorestframework django-cors-headers djangorestframework-simplejwt django-filter
python manage.py makemigrations mybustimes
python manage.py migrate
call runAPI.bat