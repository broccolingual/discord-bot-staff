#!/bin/bash

readonly SCREEN_NAME='bot'

if [ -n "$(screen -list | grep -o "${SCREEN_NAME}")" ]; then
	echo 'bot is already running'	
else
	echo 'starting bot'
	screen -AmdS $SCREEN_NAME python3 main.py
fi