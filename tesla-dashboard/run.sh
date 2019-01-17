#!/bin/bash

. /home/mattm/env/bin/activate
python3 -u -m flask run -h 0.0.0.0 -p 443 --cert /etc/letsencrypt/live/tesla.narabox.com/fullchain.pem --key /etc/letsencrypt/live/tesla.narabox.com/privkey.pem
