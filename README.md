# duo_phone_cleanup

This script cleans up phones in the limbo state of "Generic Smartphone" in [Duo Security].

# The issue

If a user starts setting up a phone during the Duo registration, but then stops before they actually activate the phone successfully, they will be left in a state where they cannot log in.  This can lead to help desk call and a bad user experience.

Instead, we want to remove any phone in this limbo state so that the user can try again later.

# Usage

```
usage: duo_phone_cleanup [-h] [--skey SKEY] [--ikey IKEY] [--host HOST]
                   [--grace-period GRACE_PERIOD] [--force | --no-force | -f]
                   [--verbose]
                   [user ...]

        Automatically cleans up phones in the limbo state of "Generic
        Smartphone" in Duo Security.

        The first time it sees a phone, it will tag it (on Duo) with a timestamp.
        On the next run, if that timestamp is older than the specified grace
        period, it will be removed.

        All arguments except the positional `user` can also be environment
        variables, e.g. `--skey` can also be provided as the environment
        variable `DUO_SKEY`
        

positional arguments:
  user                  A specific user to operate upon. Can be repeated. Not
                        required.

options:
  -h, --help            show this help message and exit
  --skey SKEY, -s SKEY  Duo Secret key. Remember that "The security of your
                        Duo application is tied to the security of your secret
                        key (skey). Secure it as you would any sensitive
                        credential. Don't share it with unauthorized
                        individuals or email it to anyone under any
                        circumstances!"
  --ikey IKEY, -i IKEY  Duo Integration key
  --host HOST, -H HOST  Address of the Duo SSO API application, e.g.
                        api-<yourid>.duosecurity.com
  --grace-period GRACE_PERIOD, -g GRACE_PERIOD
                        The maximum duration (in minutes) that this tool will
                        allow a "Generic Smartphone" to remain registered once
                        it has been tagged by a prior run."
  --force, --no-force, -f
                        If negated with `--no-force`, this tool will prompt
                        for confirmation before deleting each "Generic
                        Smartphone" device (default: True)
  --verbose, -v         Set output verbosity (-v=warning, -vv=debug)

examples:

        duo_phone_cleanup <args>
    
```

# How it works

This script is intended to be run on a regular interval (e.g. Cron)

1. The first time it processed a device with the platform `Generic Smartphone`, it assigns a timestamp in the Duo API.
1. If the grace period (default 10 minutes) has passed when the phone is processed on subsequent runs, it will be removed.

The grace period is intended not to interrupt a user who may be actively setting up their smartphone (the timeout to setup a new phone  on the Duo end seems to be about 17 minutes?)

The script starts by enumerating through the users in Duo.  It checks each users phone to see if it is in the "Generic Smartphone" state. If so, it then determines if the phone has been in this state for longer than the grace period.  Since Duo does not record when a phone was registered, we need to store the time when this script first sees the phone.  We have to save this information somewhere.  Rather than creating a local database to be maintained, we utilize the often ignored "Name" field that Duo uses to store the name of a phone.  Since this field is blank by default, we store the seconds since the epoch when we first see the phone in this field.  If a date is already in this field, we check if it is beyond the grace period.  If it is, we remove the phone.

This should be safe, but YMMV, so please be careful!

# Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

To run the test suite:

```bash
# Dependent targets create venv and install dependencies
make
```

Please make sure to update tests along with any changes.

# License

[License :: OSI Approved :: MIT License](#LICENSE)


[Duo Security]: https://duo.com/docs/administration
[LICENSE]: LICENSE
