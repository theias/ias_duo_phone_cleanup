#!/usr/bin/env python3
"""
Cleanup Duo accounts.
"""

import argparse
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict


# Duo phones in the API have no hidden metadata fields or anything, so we're
# using the `name` field which starts out empty. This could change if we
# discover some field more appropriate for our metadata in the future
from duo import PHONE_TIMESTAMP_KEY, Duo, ProcessPhoneResult


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


def user_verify(prompt: str) -> bool:
    """Get user verifcation before an action"""
    print(f"{prompt} [y/n]")
    while True:
        try:
            inp = input().lower()
            logging.debug("User input for prompt `%s`: `%s`", prompt, inp)
            return strtobool(inp)
        except ValueError:
            print("Please respond with 'y' or 'n'")


def main(
    argv: list = sys.argv[1:],
) -> None:
    """main"""
    args = parse_args(argv)
    args_redacted: Dict[str, Any] = {
        # Redact the secret key
        k: f"{v[0]}{'*'*len(v)}{v[-1]}" if k == "skey" else v
        for k, v in vars(args).items()
    }
    logging.debug("Argparse results: %s", args_redacted)
    logging.info(
        "Will use the field `%s` to check/store timestamps for phones",
        PHONE_TIMESTAMP_KEY,
    )
    # Retrieve user info from API:
    duo: Duo = Duo(ikey=args.ikey, skey=args.skey, host=args.host)
    processed: defaultdict = defaultdict(int)
    res: ProcessPhoneResult
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
                res = duo.process_phone(phone=phone, time_cutoff=grace_period_time)
                processed[res] += 1
            else:
                res = duo.process_phone(
                    phone=phone, time_cutoff=grace_period_time, pre_test=user_verify
                )
            processed[res] += 1
        else:
            logging.debug(
                "Phone `%s` for user `%s` not `Generic Smartphone`, taking no action",
                phone["phone_id"],
                phone["username"],
            )
            processed[ProcessPhoneResult.NO_ACTION] += 1
    logging.info(
        "Processing complete. {timestamped: %s, removed: %s, no_action: %s",
        processed[ProcessPhoneResult.TIMESTAMPED],
        processed[ProcessPhoneResult.REMOVED],
        processed[ProcessPhoneResult.NO_ACTION],
    )


if __name__ == "__main__":
    main(sys.argv[1:])
