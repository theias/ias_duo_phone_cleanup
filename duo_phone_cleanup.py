#!/usr/bin/env -S /usr/bin/python -Wall -Wignore::DeprecationWarning
"""
Cleanup Duo accounts.
"""

import os
import smtplib
import sys
import time
import csv
import duo_client
import configparser
from datetime import datetime, timedelta

config = configparser.ConfigParser()
config.read('credentials.ini')

# Configuration and information about objects to create.
admin_api = duo_client.Admin(
    ikey=config['duo']['ikey'],
    skey=config['duo']['skey'],
    host=config['duo']['host'],
)

GRACE_PERIOD_MINUTES = 10 # minutes to allow generic smartphone
now = datetime.utcnow()
grace_period = now - timedelta(minutes=GRACE_PERIOD_MINUTES)

def get_users():
    try:
        return admin_api.get_users()
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def get_phones():
    try:
        return admin_api.get_phones()
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def remove_generic_smartphone(user):
    try:
        user_id = user['user_id']
        phones = user['phones']

        for phone in phones:
            if 'generic smartphone' in phone['platform'].lower():
                phone_full = admin_api.get_phone_by_id(phone_id=phone['phone_id'])
                # Check if the user was added before the grace period
                phone_created = datetime.fromtimestamp(int(phone['name'] or 0))
                if phone['name'] == '':
                    # Update the date last seen in the name field
                    print(f"I need to update the phone name with the date")
                    print(f"Updating {phone['phone_id']} with now {round(datetime.timestamp(now))}")
                    admin_api.update_phone(phone_id=phone['phone_id'], name=str(round(datetime.timestamp(now))))
                elif phone_created < grace_period:
                    # Delete the generic smartphone entry
                    print(f"Delete generic smartphone: {phone['phone_id']} for user {user_id}")
                    print(f"Now: {now} GRACE_PERIOD_MINUTES: {GRACE_PERIOD_MINUTES}")
                    print(f"Added at: {phone_created}, Grace Period = {grace_period}")
                    admin_api.delete_phone(phone['phone_id'])
    except Exception as e:
        print(f"Error: {str(e)}")

# Retrieve user info from API:
users = get_users()
for user in users:
    remove_generic_smartphone(user)
