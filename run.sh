#!/bin/bash

. venv/bin/activate
FLASK_APP=serv.py FLASK_ENV=development flask run --host=0.0.0.0
