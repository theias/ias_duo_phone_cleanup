#!/usr/bin/env python3
"""
Cleanup Duo accounts.
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List

import duo_client  # type:ignore

# Duo phones in the API have no hidden metadata fields or anything, so we're
# using the `name` field which starts out empty. This could change if we
# discover some field more appropriate for our metadata in the future
PHONE_TIMESTAMP_KEY = "name"


def strtobool(val):
    """
    Stolen from deprecated `distutils.util.strtobool`

    Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return 1
    if val in ("n", "no", "f", "false", "off", "0"):
        return 0

    raise ValueError(f"invalid truth value {val}")


def parse_args(argv=None) -> argparse.Namespace:
    """Parse args"""

    bool_action = (
        # Should be `BooleanOptionalAction` if Python >= 3.9, else the old way
        argparse.BooleanOptionalAction
        if hasattr(argparse, "BooleanOptionalAction")
        else "store_true"
    )

    usage_examples: str = """examples:

        %(prog)s <args>
    """
    descr: str = """
        Automatically cleans up phones in the limbo state of "Generic
        Smartphone" in Duo Security.

        The first time it sees a phone, it will tag it (on Duo) with a timestamp.
        On the next run, if that timestamp is older than the specified grace
        period, it will be removed.

        All arguments except the positional `user` can also be environment
        variables, e.g. `--skey` can also be provided as the environment
        variable `DUO_SKEY`
        """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description=descr,
        epilog=usage_examples,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--skey",
        "-s",
        default=os.environ.get("DUO_SKEY", None),
        help=(
            'Duo Secret key. Remember that "The security of your Duo '
            "application is tied to the security of your secret key (skey). "
            "Secure it as you would any sensitive credential. Don't share it "
            "with unauthorized individuals or email it to anyone under any "
            'circumstances!"'
        ),
        type=str,
    )

    parser.add_argument(
        "--ikey",
        "-i",
        default=os.environ.get("DUO_IKEY", None),
        help=("Duo Integration key"),
        type=str,
    )

    parser.add_argument(
        "--host",
        "-H",
        default=os.environ.get("DUO_HOST", None),
        help=(
            "Address of the Duo SSO API application, e.g. api-<yourid>.duosecurity.com"
        ),
        type=str,
    )

    parser.add_argument(
        "--grace-period",
        "-g",
        default=os.environ.get("DUO_GRACE_PERIOD", 10),
        help=(
            "The maximum duration (in minutes) that this tool will allow a "
            '"Generic Smartphone" to remain registered once it has been tagged '
            'by a prior run."'
        ),
        type=int,
    )

    parser.add_argument(
        "--force",
        "-f",
        action=bool_action,  # type:ignore
        default=os.environ.get("DUO_FORCE", True),
        help=(
            "If negated with `--no-force`, this tool will prompt for confirmation "
            'before deleting each "Generic Smartphone" device'
        ),
        type=bool,
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        dest="verbosity",
        help="Set output verbosity (-v=warning, -vv=debug)",
    )

    parser.add_argument(
        "users",
        help=("A specific user to operate upon. Can be repeated. Not required."),
        metavar="user",
        nargs="*",
        type=str,
    )

    args = parser.parse_args(argv) if argv else parser.parse_args()

    if args.verbosity >= 2:
        log_level = logging.DEBUG
    elif args.verbosity >= 1:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING

    logging.basicConfig(
        format="%(asctime)s,%(levelname)s,%(message)s",
        level=log_level,
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    return args


# pylint: disable=too-few-public-methods
class Duo:
    """
    Duo Security API

    Choosing to leave this quite sparse due to our very simple use case

    Puts the users in `self.users` and puts the phones into `self.phones`.
    The phones are as they come from Duo, except with the `username` and
    `user_id` added in so they can be operated upon on their own in this
    program's context.

    Use
    """

    def __init__(self, *, ikey, skey, host):
        logging.debug("Connecting to Duo API at host %s", host)
        self.api: duo_client.Admin = duo_client.Admin(ikey=ikey, skey=skey, host=host)
        logging.info("Fetching user list from Duo API")
        try:
            self.users: Iterable = self.api.get_users()
        except Exception as err:  # pylint: disable=broad-except
            # The Duo module barely handles its own exceptions so we have
            # little choice here
            logging.error(
                (
                    "Unknown problem fetching users from Duo. It may not have "
                    "been able to connect, or the credentials may be incorrect. "
                ),
            )
            raise err
        logging.info("%d users fetched from Duo", len(self.users))  # type:ignore
        logging.debug(
            "users fetched from Duo: `%s`", [u["username"] for u in self.users]
        )
        self.phones: List[dict] = []
        for user in self.users:
            updates = {"username": user["username"], "user_id": user["user_id"]}
            user_phones: List[dict] = user["phones"]
            for phone in user_phones:
                phone.update(updates)
                self.phones.append(phone)

    def process_phone(
        self,
        pre_test: Callable = lambda x: True,
        *,
        phone: Dict[str, Any],
        time_cutoff: datetime,
    ) -> None:
        """
        Remove a phone if its timestamp is old enough, else create the timestamp

        Optionally will call specified `pre_test(`prompt`) before making any actual
        writes or deletes, and skip the operation if it returns falsey
        """
        created_time = datetime.fromtimestamp(int(phone[PHONE_TIMESTAMP_KEY] or 0))
        logging.debug(
            "Processing phone for user `%s` with id `%s`, with timestamp value `%s`",
            phone["username"],
            phone["phone_id"],
            phone[PHONE_TIMESTAMP_KEY],
        )
        if not created_time.timestamp() and pre_test(
            f'Write timestamp to `name` field for {phone["username"]}\'s phone '
            f'`{phone["phone_id"]}`?'
        ):
            # If there is no existing Unix time value in our metadata field,
            # place one
            logging.info(
                (
                    "Updating new phone for the user `%s` with id "
                    "`%s` with timestamp, to mark for cleanup on the "
                    "next run"
                ),
                phone["username"],
                phone["phone_id"],
            )
            self.api.update_phone(
                phone_id=phone["phone_id"],
                name=str(round(datetime.timestamp(datetime.utcnow()))),
            )
        elif created_time < time_cutoff and pre_test(
            f'Remove {phone["username"]}\'s phone `{phone["phone_id"]}`?'
        ):
            # Else if the phone was timestamped with a value before our grace
            # period, delete
            logging.info(
                "Deleting phone for the user `%s` with id `%s`",
                phone["username"],
                phone["phone_id"],
            )
            self.api.delete_phone(phone["phone_id"])
        else:
            logging.debug(
                ("Taking no action on phone for the user `%s` with id `%s`"),
                phone["username"],
                phone["phone_id"],
            )


# pylint: enable=too-few-public-methods


def user_verify(prompt) -> str:
    """TODO"""
    print(f"{prompt} [y/n]")
    while True:
        try:
            inp = input().lower()
            logging.debug("User input for prompt `%s`: `%s`", prompt, inp)
            return strtobool(inp)
        except ValueError:
            print("Please respond with 'y' or 'n'")


def main(
    argv,
) -> None:
    """main"""
    args = parse_args(argv)
    logging.debug("Argparse results: %s", args)
    logging.info(
        "Will use the field `%s` to check/store timestamps for phones",
        PHONE_TIMESTAMP_KEY,
    )
    # Retrieve user info from API:
    duo: Duo = Duo(ikey=args.ikey, skey=args.skey, host=args.host)
    # Operate on phones where appropriate
    for phone in duo.phones:
        if args.users and phone["username"] not in args.users:
            # If we have specific users to operate upon and this is not one of
            # them
            logging.debug(
                (
                    "Skipping phone `%s` for user `%s` - not in the list of users to "
                    "operate upon"
                ),
                phone["phone_id"],
                phone["username"],
            )
            continue
        if phone["platform"].lower() == "generic smartphone":
            grace_period_time = datetime.utcnow() - timedelta(
                minutes=int(args.grace_period)
            )
            if args.force:
                duo.process_phone(phone=phone, time_cutoff=grace_period_time)
            else:
                duo.process_phone(
                    phone=phone, time_cutoff=grace_period_time, pre_test=user_verify
                )
        else:
            logging.debug(
                "Phone `%s` for user `%s` not `Generic Smartphone`, taking no action",
                phone["phone_id"],
                phone["username"],
            )


if __name__ == "__main__":
    main(sys.argv[1:])
