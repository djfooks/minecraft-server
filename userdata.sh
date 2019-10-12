#!/bin/bash

add-apt-repository ppa:openjdk-r/ppa -y
apt update
apt install openjdk-8-jre -y
apt install python -y
apt install screen -y
mkdir /data

wget https://raw.githubusercontent.com/djfooks/minecraft-server/master/minecraft-http.py
python minecraft-http.py
