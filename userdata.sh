#!/bin/bash

apt update
apt install python screen awscli zip -y

wget https://raw.githubusercontent.com/djfooks/minecraft-server/master/minecraft-http.py
python minecraft-http.py API_KEY
