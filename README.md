# ias_duo_phone_cleanup
This script will automatically clean up phones in the limbo state of "Generic Smartphone" in Duo Security.

#############
# The issue #
#############

If a user starts setting up a phone during the Duo registration,
but then stops before they actually activate the phone successfully,
they will be left in a state where they cannot log in.  This can lead
to helpdesk call and a bad user experience.  Instead, we want to remove
any phone in this limbo state so that the user can try again later.

################
# How it works #
################

The script sets a grace period where a user may be actively setting up
their smartphone.  By default this is 10 minutes.  The script is meant
to run on a periodic basis, maybe every 10 minutes.  This means, that a
phone could be in a limbo state for 10-20 minutes before being removed.
Reconfigure as you see fit.

The timeout to setup a new phone seems to be about 17 minutes (1024 seconds?).

The script starts by enumerating through the users in Duo.  It checks
each users phone to see if it is in the "Generic Smartphone" state.
If so, it then determines if the phone has been in this state for
longer than the grace period.  Since Duo does not record when a phone
was registered, we need to store the time when this script first sees
the phone.  We have to save this information somewhere.  Rather than
creating a local database to be maintained, we utilize the often ignored
"Name" field that Duo uses to store the name of a phone.  Since this
field is blank by default, we store the seconds since the epoch when we
first see the phone in this field.  If a date is already in this field,
we check if it is beyond the grace period.  If it is, we remove the phone.

This should be safe, but YMMV, so please be careful

#################
# How to use it #
#################

The script needs the keys from an Admin API application in Duo Security
to work.  Please set this up and copy the values into the file.  You can
use the credentials_template.ini as a template like so.

$ cp credentials_template.ini credentials.ini
$ vi credentials.ini

Make sure you have all the required Python libraries.

$ pip install -r requirements.txt

Run the script like this

$ ./duo_phone_cleanup.py

