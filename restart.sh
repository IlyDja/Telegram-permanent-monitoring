#!/bin/bash

# Первая сессия для userbot.py
screen -S userbot
cd /root/
source /root/venv/bin/activate
python userbot.py

# Вторая сессия для TGPMwithoutGUI.py
screen -S parser
cd /root/____PARSER2____
source /root/____PARSER2____/my_env/bin/activate
/usr/bin/python3.13 TGPMwithoutGUI.py



