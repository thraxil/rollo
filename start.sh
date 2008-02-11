#!/bin/bash
cd $1
export PYTHON_EGG_CACHE=/var/www/rollo/.python-eggs
source working-env/bin/activate
exec ./start-rollo.py $2 

