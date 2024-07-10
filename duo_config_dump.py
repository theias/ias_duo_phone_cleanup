#!/usr/bin/env -S /usr/bin/python -Wall -Wignore::DeprecationWarning
"""
Detect webauthn users without phones
"""

import os
import smtplib
import sys
import csv
import json
import pprint
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

# Retrieve user info from API:
integrations = admin_api.get_integrations()
for integration in integrations:
    print(f"Integration: {integration['name']}")
    pprint.pprint(integration)
    print(f"")

policies = admin_api.get_policies_v2()
for policy in policies:
    print(f"Policy: {policy['policy_name']}")
    pprint.pprint(policy)
    print(f"")

policy_summary = admin_api.get_policy_summary_v2()
print(f"Policy Summary")
pprint.pprint(policy_summary)
print(f"")

groups = admin_api.get_groups()
for group in groups:
    print(f"Group: {group['name']}")
    pprint.pprint(group)
    group_users = admin_api.get_group_users(group['group_id'])
    pprint.pprint(group_users)
    print(f"")
