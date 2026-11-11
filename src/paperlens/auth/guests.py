import time

from paperlens.indexing.vector_store import get_collection

GUEST_TTL_SECONDS = 2 * 60 * 60

# Guest step: temporary records of the guest sessions (they are lost when the server restarts, on purpose)
guests = {}


# Guest step: start a record for a new guest session
def register_guest(guest_id):
    guests[guest_id] = {"created": time.time(), "documents": [], "queries": 0}


# Guest step: get the record of a guest, and create it if the server restarted in between
def get_guest(guest_id):
    if guest_id not in guests:
        register_guest(guest_id)

    return guests[guest_id]


# Guest step: delete everything that belongs to one guest
def delete_guest_data(guest_id):
    get_collection().delete(where={"owner_id": guest_id})
    guests.pop(guest_id, None)


# Guest step: delete the data of guests whose session is older than two hours
def purge_expired_guests():
    now = time.time()
    expired = []

    for guest_id in guests:
        if now - guests[guest_id]["created"] > GUEST_TTL_SECONDS:
            expired.append(guest_id)

    for guest_id in expired:
        delete_guest_data(guest_id)


# Guest step: on startup, delete all guest chunks left from before the restart
def purge_all_guest_data():
    data = get_collection().get(include=["metadatas"])
    owners = []

    for meta in data["metadatas"]:
        owner = meta["owner_id"]
        if owner.startswith("guest:") and owner not in owners:
            owners.append(owner)

    for owner in owners:
        get_collection().delete(where={"owner_id": owner})

    guests.clear()
