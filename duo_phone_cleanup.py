#!/usr/bin/env -S /usr/bin/python -Wall -Wignore::DeprecationWarning
"""
Cleanup Duo accounts.
"""

import configparser
import csv
import duo_client
import getopt
import os
import smtplib
import sys
import time
from datetime import datetime, timedelta

config = configparser.ConfigParser()
config.read('credentials.ini')

# Configuration and information about objects to create.
admin_api = duo_client.Admin(
    ikey=config['duo']['ikey'],
    skey=config['duo']['skey'],
    host=config['duo']['host'],
)

grace_period_minutes=int(config['duo']['grace_period_minutes'])
now = datetime.utcnow()
grace_period = now - timedelta(minutes=grace_period_minutes)

delete = 0 # by default report only

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
    global delete
    try:
        user_id = user['user_id']
        username = user['username']
        phones = user['phones']

        for phone in phones:
            if 'generic smartphone' in phone['platform'].lower():
                phone_full = admin_api.get_phone_by_id(phone_id=phone['phone_id'])
                # Check if the user was added before the grace period
                phone_created = datetime.fromtimestamp(int(phone['name'] or 0))
                if phone['name'] == '':
                    # Update the date last seen in the name field
                    print(f"Updating {phone['phone_id']} for {username} with now {round(datetime.timestamp(now))}")
                    if delete == 1:
                        admin_api.update_phone(phone_id=phone['phone_id'], name=str(round(datetime.timestamp(now))))
                elif phone_created < grace_period:
                    # Delete the generic smartphone entry
                    print(f"Delete generic smartphone: {phone['phone_id']} for user {username} {user_id}")
                    print(f"Now: {now} GRACE_PERIOD_MINUTES: {grace_period_minutes}")
                    print(f"Added at: {phone_created}, Grace Period = {grace_period}")
                    if delete == 1:
                        admin_api.delete_phone(phone['phone_id'])
    except Exception as e:
        print(f"Error: {str(e)}")

def main(argv):
    global delete
    global grace_period_minutes
    global grace_period
    foruser = ""
    try:
        opts, args = getopt.getopt(argv[1:],"dg:u:")
    except getopt.GetoptError:
        print(f"{argv[0]} [-d] [-u username]")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-d':
            delete = 1
        if opt == '-u':
            foruser = arg
        if opt == '-g':
            grace_period_minutes = int(arg)
            grace_period = now - timedelta(minutes=grace_period_minutes)
            print(f"Grace period set to {grace_period_minutes} minutes")

    if delete == 1:
        print(f"Delete option is active")
    else:
        print(f"Delete option is not active")

    if foruser != '':
        print(f"Operating only for user {foruser}")

    # Retrieve user info from API:
    users = get_users()
    for user in users:
        if foruser == '' or user['username'] == foruser:
            remove_generic_smartphone(user)

if __name__ == "__main__":
    main(sys.argv)
