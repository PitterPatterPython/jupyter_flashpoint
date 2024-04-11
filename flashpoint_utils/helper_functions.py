import argparse
import base64
from datetime import datetime
from IPython import get_ipython

ipy = get_ipython()

def create_b64_image_string(raw_image):
    """Convert a raw bytes image to a base64 string"""
    return base64.b64encode(raw_image).decode()


def format_b64_image_for_dataframe(b64_image_string):
    """Format a b64 image string as a valid HTML object, to be
        used in a dataframe.
    """
    return f"<img src='data:image/jpeg;base64,{b64_image_string}' />"


def valid_date_format(date_from_argparse):
    if date_from_argparse.lower() == 'now':
        return datetime.now().date()
    try:
        return datetime.strptime(date_from_argparse, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Not a valid date: {date_from_argparse}")


def valid_list(user_list):
    if user_list not in ipy.user_ns:
        raise argparse.ArgumentTypeError(f'The list "{user_list}" is not currently loaded. Are you \
            sure that it exists and the call has been loaded?')
    else:
        return ipy.user_ns[user_list]


def valid_query(user_query):
    """If the user encapsulated their query with single quotes (they'd do this
        if they're trying to run a complex query), remove the quotes so we can
        avoid HTTP 400 errors (aka pass a valid query to the Flashpoint API)"""
    if user_query.startswith("'") and user_query.endswith("'"):
        return user_query[1:-1]
    return user_query
