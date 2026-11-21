import time

from fastapi import HTTPException

# Rate limit step: the times of the latest requests of every IP address, kept in memory (lost when the server restarts)
hits = {}


# Rate limit step: the IP address of the visitor, read from the headers that Cloudflare and Render add
def client_ip(request):
    for name in ["cf-connecting-ip", "true-client-ip", "x-forwarded-for"]:
        value = request.headers.get(name)
        if value:
            return value.split(",")[0].strip()

    return ""


# Rate limit step: stop with 429 when one IP address asks too often; without an IP address nobody is blocked
def check_rate(request, name, limit, window_seconds, message):
    ip = client_ip(request)
    if ip == "":
        return

    key = name + ":" + ip
    now = time.time()

    recent = []
    for moment in hits.get(key, []):
        if now - moment < window_seconds:
            recent.append(moment)

    if len(recent) >= limit:
        hits[key] = recent
        raise HTTPException(status_code=429, detail=message)

    recent.append(now)
    hits[key] = recent

    # Keep the memory small: forget the addresses that were not seen for a day
    if len(hits) > 5000:
        for old_key in list(hits.keys()):
            if len(hits[old_key]) == 0 or now - hits[old_key][-1] > 86400:
                hits.pop(old_key, None)
