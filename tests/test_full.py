"""
Test end-to-end functionality with a parameterized list of inputs and expected results

mock the bits of the Duo API that get touched by our script and verify the results
"""
# pylint: disable=global-statement

import json
from typing import Any, List

import duo_client  # type:ignore
import pytest  # type:ignore

import duo_phone_cleanup.__main__ as program  # type:ignore


MOCK_GET_USERS_CALLED_COUNT: int = 0
MOCK_DELETE_PHONE_CALLED: list = []
MOCK_UPDATE_PHONE_CALLED: list = []


# pylint: disable=unused-argument
# pylint: disable=global-variable-not-assigned
def mock_update_phone(_, *, phone_id: str, name: str) -> Any:
    """
    Just succeed and do not raise any exceptions

    Should return some object but we don't care as long as it did not raise any
    Exceptions
    """
    global MOCK_UPDATE_PHONE_CALLED
    MOCK_UPDATE_PHONE_CALLED.append({"phone_id": phone_id})
    return True


def mock_get_users(_) -> List[dict]:
    """Return the users as Python list"""
    global MOCK_GET_USERS_CALLED_COUNT
    MOCK_GET_USERS_CALLED_COUNT += 1
    with open("tests/users.json", mode="r", encoding="utf-8") as userfile:
        return json.load(userfile)


def mock_delete_phone(_, phone_id: str) -> Any:
    """
    Just succeed and do not raise any exceptions

    This should be returning a `requests.Response` object but the Duo module
    does no type checking and we have no use for the return value, so
    """
    global MOCK_DELETE_PHONE_CALLED
    MOCK_DELETE_PHONE_CALLED.append({"phone_id": phone_id})
    return True


# pylint: enable=global-variable-not-assigned
# pylint enable=unused-argument


@pytest.mark.parametrize(
    "test_input,expected",
    # The test users list includes three users so we can test different
    # scenarios:
    #
    # * one user with a "Generic Smartphone" and no timestamp (`barret`)
    #   - Should generally only get stamped, not deleted
    # * one user with a "Generic Smartphone" and very old timestamp (`cloud`)
    #   - Should generally be deleted
    # * one more user with a "Generic Smartphone" and very old timestamp (`sephiroth`)
    #   - Should generally be deleted
    # * one user with a fully registered iPhone (`redxxi`)
    #   - should never be touched
    # * one user with a "Generic Smartphone" and far future timestamp `(`tifa`)
    #   - Should not be deleted as the stamp is not older than the grace period
    #     (unless we're still running these tests in the year 4876)
    #
    # Now here are the sets of inputs and their matching results that we are
    # testing for
    [
        (
            # * Operate on all phones with platform `Generic Smartphone`
            [
                "--skey",
                "myskey",
                "--ikey",
                "myikey",
                "--host",
                "myhost.domain.tld",
                "-vvv",
            ],
            {
                "MOCK_GET_USERS_CALLED_COUNT": 1,
                "MOCK_UPDATE_PHONE_CALLED": [{"phone_id": "barret_phone_1"}],
                "MOCK_DELETE_PHONE_CALLED": [
                    {"phone_id": "cloud_phone_1"},
                    {"phone_id": "sephiroth_phone_1"},
                ],
            },
        ),
        (
            # * Operate on all phones with platform `Generic Smartphone
            # * BUT require user input for each write/delete action (no `--no-force`)
            #   - mocking of user input is arranged in the test itself
            [
                "--skey",
                "myskey",
                "--ikey",
                "myikey",
                "--host",
                "myhost.domain.tld",
                "--no-force",
                "-vvv",
            ],
            {
                "MOCK_GET_USERS_CALLED_COUNT": 1,
                "MOCK_UPDATE_PHONE_CALLED": [{"phone_id": "barret_phone_1"}],
                "MOCK_DELETE_PHONE_CALLED": [
                    {"phone_id": "cloud_phone_1"},
                    {"phone_id": "sephiroth_phone_1"},
                ],
            },
        ),
        (
            # * Specify one user with a "Generic Smartphone" with no timestamp
            # * should update the device
            # * no others should be operated upon
            [
                "--skey",
                "myskey",
                "--ikey",
                "myikey",
                "--host",
                "myhost.domain.tld",
                "-vvv",
                "barret",
            ],
            {
                "MOCK_GET_USERS_CALLED_COUNT": 1,
                "MOCK_UPDATE_PHONE_CALLED": [
                    {"phone_id": "barret_phone_1"},
                ],
                "MOCK_DELETE_PHONE_CALLED": [],
            },
        ),
        (
            # * Specify one user with a "Generic Smartphone" to be deleted
            # * no others should be operated upon
            [
                "--skey",
                "myskey",
                "--ikey",
                "myikey",
                "--host",
                "myhost.domain.tld",
                "-vvv",
                "cloud",
            ],
            {
                "MOCK_GET_USERS_CALLED_COUNT": 1,
                "MOCK_UPDATE_PHONE_CALLED": [],
                "MOCK_DELETE_PHONE_CALLED": [
                    {"phone_id": "cloud_phone_1"},
                ],
            },
        ),
        (
            # * Specify multiple users with a "Generic Smartphone" to be deleted
            # * only those should be operated upon
            [
                "--skey",
                "myskey",
                "--ikey",
                "myikey",
                "--host",
                "myhost.domain.tld",
                "-vvv",
                "cloud",
                "sephiroth",
            ],
            {
                "MOCK_GET_USERS_CALLED_COUNT": 1,
                "MOCK_UPDATE_PHONE_CALLED": [],
                "MOCK_DELETE_PHONE_CALLED": [
                    {"phone_id": "cloud_phone_1"},
                    {"phone_id": "sephiroth_phone_1"},
                ],
            },
        ),
    ],
    ids=[
        "Operate on all phones with platform `Generic Smartphone`",
        (
            "Operate on all phones with platform `Generic Smartphone * BUT require "
            "user input for each write/delete action (no `--no-force`) - mocking of "
            "user input is arranged in the test itself"
        ),
        (
            "Specify one user with a 'Generic Smartphone' with no timestamp. Should "
            "update the device. No others should be operated upon"
        ),
        (
            "Specify one user with a 'Generic Smartphone' to be deleted. No others "
            "should be operated upon"
        ),
        (
            "Specify multiple users with a 'Generic Smartphone' to be deleted. Only "
            "those should be operated upon"
        ),
    ],
)
def test_end_to_end(monkeypatch, test_input, expected):
    """Test"""
    global MOCK_GET_USERS_CALLED_COUNT
    global MOCK_UPDATE_PHONE_CALLED
    global MOCK_DELETE_PHONE_CALLED
    MOCK_GET_USERS_CALLED_COUNT = 0
    MOCK_UPDATE_PHONE_CALLED = []
    MOCK_DELETE_PHONE_CALLED = []
    monkeypatch.setattr(duo_client.Admin, "get_users", mock_get_users)
    monkeypatch.setattr(duo_client.Admin, "update_phone", mock_update_phone)
    monkeypatch.setattr(duo_client.Admin, "delete_phone", mock_delete_phone)
    monkeypatch.setattr("builtins.input", lambda: "y")  # Always input yes

    program.main(argv=test_input)

    assert (
        MOCK_GET_USERS_CALLED_COUNT == expected["MOCK_GET_USERS_CALLED_COUNT"]
    ), "`get_users` was not called the expected number of times"
    assert (
        MOCK_UPDATE_PHONE_CALLED == expected["MOCK_UPDATE_PHONE_CALLED"]
    ), "`update_phone` was not called for the expected phones"
    assert (
        MOCK_DELETE_PHONE_CALLED == expected["MOCK_DELETE_PHONE_CALLED"]
    ), "`delete_phone` was not called for the expected phones"
