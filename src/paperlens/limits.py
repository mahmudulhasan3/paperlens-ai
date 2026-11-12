import os

from dotenv import load_dotenv

load_dotenv()


# Limits step: read a whole number from the .env file, or use the default
def read_number(name, default):
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


GUEST_MAX_PDFS = read_number("GUEST_MAX_PDFS", 2)
GUEST_MAX_FILE_MB = read_number("GUEST_MAX_FILE_MB", 10)
GUEST_MAX_QUERIES = read_number("GUEST_MAX_QUERIES", 15)

USER_MAX_PDFS = read_number("USER_MAX_PDFS", 20)
USER_MAX_FILE_MB = read_number("USER_MAX_FILE_MB", 25)
USER_DAILY_QUERIES = read_number("USER_DAILY_QUERIES", 100)
