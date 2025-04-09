#!/bin/bash
set -e
source env/bin/activate
python3 mybustimesAPI/manage.py runserver 0.0.0.0:8000 &
sleep 5
node index.js