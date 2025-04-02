set -e
python -m venv env
source env/bin/activate
pip install --upgrade pip
pip install django djangorestframework django-cors-headers djangorestframework-simplejwt django-filter
python manage.py makemigrations mybustimes
python manage.py migrate
bash runAPI.sh