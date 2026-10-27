"""Write a contact plan for ION, HDTN, or as plain JSON."""
import json
import math


def ion(contacts):
    """ionadmin commands. ION rates are bytes per second, ranges whole seconds of light time."""
    lines = []
    for c in contacts:
        lines.append(f"a contact +{int(c.start)} +{int(math.ceil(c.end))} {c.a} {c.b} {c.rate_bps // 8}")
    for c in contacts:
        lines.append(f"a range +{int(c.start)} +{int(math.ceil(c.end))} {c.a} {c.b} {int(math.ceil(c.owlt_s))}")
    return "\n".join(lines) + "\n"


def hdtn(contacts):
    """HDTN contact plan JSON (times in seconds from start, rate in bits per second)."""
    return json.dumps({"contacts": [
        {"contact": i + 1, "source": c.a, "dest": c.b, "startTime": int(c.start), "endTime": int(math.ceil(c.end)),
         "rateBitsPerSec": c.rate_bps, "owlt": int(math.ceil(c.owlt_s))}
        for i, c in enumerate(contacts)]}, indent=1) + "\n"


def plain(contacts, start_iso):
    return json.dumps({"start": start_iso, "contacts": [
        {"from": c.a, "to": c.b, "start_s": round(c.start, 1), "end_s": round(c.end, 1),
         "duration_s": round(c.end - c.start, 1), "rate_bps": c.rate_bps, "owlt_s": round(c.owlt_s, 3), "via": c.via}
        for c in contacts]}, indent=1) + "\n"
