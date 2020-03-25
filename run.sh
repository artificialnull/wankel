#!/bin/bash

. venv/bin/activate
FLASK_APP=serv.py FLASK_ENV=production flask run --host=0.0.0.0 --port=80 #--cert=fullchain.pem --key=privkey.pem
