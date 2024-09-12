#!/usr/bin/env -S /usr/bin/python3 -Wall -Wignore::DeprecationWarning
"""
Detect webauthn users without phones
"""

import os
import smtplib
import sys
import csv
import duo_client
import configparser

config = configparser.ConfigParser()
config.read('credentials.ini')

# Configuration and information about objects to create.
admin_api = duo_client.Admin(
    ikey=config['duo']['ikey'],
    skey=config['duo']['skey'],
    host=config['duo']['host'],
)

def get_users():
    try:
        return admin_api.get_users()
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def detect_webauthn_without_phone(user):
    try:
        user_id = user['user_id']
        phones = user['phones']
        if len(user['webauthncredentials']) > 0 and len(user['phones']) == 0:
            print(f"User: {user['username']} WebAuthN: {user['webauthncredentials']}")

    except Exception as e:
        print(f"Error: {str(e)}")

# Retrieve user info from API:
users = get_users()
for user in users:
    detect_webauthn_without_phone(user)
