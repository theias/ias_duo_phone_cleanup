"""
Sparse abstraction for working with the duo client api
"""

import logging
import sys
from datetime import datetime
from enum import Enum, auto
from typing import Any, Callable, Dict, Iterable, List

import duo_client  # type:ignore

logger = logging.getLogger(__name__)
PHONE_TIMESTAMP_KEY = "name"

# pylint: disable=too-few-public-methods


class ProcessPhoneResult(Enum):
    """Results from duo phone update"""

    TIMESTAMPED = auto()
    REMOVED = auto()
    NO_ACTION = auto()


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
        except Exception:  # pylint: disable=broad-except
            # The Duo module barely handles its own exceptions so we have
            # little choice here
            logging.error(
                (
                    "Unknown problem fetching users from Duo. It may not have "
                    "been able to connect, or the credentials may be incorrect. "
                ),
            )
            sys.exit(1)
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
    ) -> ProcessPhoneResult:
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
            return ProcessPhoneResult.TIMESTAMPED
        if created_time < time_cutoff and pre_test(
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
            return ProcessPhoneResult.REMOVED
        logging.debug(
            ("Taking no action on phone for the user `%s` with id `%s`"),
            phone["username"],
            phone["phone_id"],
        )
        return ProcessPhoneResult.NO_ACTION


# pylint: enable=too-few-public-methods
