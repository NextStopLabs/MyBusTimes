set -e
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install django djangorestframework django-cors-headers djangorestframework-simplejwt django-filter Pillow webcolors
npm install
./dbupdate.sh
