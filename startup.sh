#!/bin/bash
apt-get update
apt-get install -y chromium

export CHROME_BIN=/usr/bin/chromium
python xAlertsBottle.py