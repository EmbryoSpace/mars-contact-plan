"""Check that ION and HDTN route through a mars-contact-plan plan as the plan says.

  python interop/check_routes.py <plan dir> <ion results dir> <hdtn results file>

For each query (source, destination, send time) the expected delivery time is the
earliest arrival over the contacts in contacts.json (a bundle may wait at a node for a
later contact; each hop adds the light time, rounded up to whole seconds as in the ION
and HDTN plans). It is compared with:

- ION: cgrfetch JSON, one file per query: ion_<src>_<dst>_<t>.json, with the plan start
  for that query (the Unix time when ion.rc was loaded) in ion_<src>_<dst>_<t>.t0
- HDTN: lines "<src> <dst> <t> <next hop> <best_delivery_time> <arrival> <hops>" or
  "<src> <dst> <t> none" from interop/hdtn_route.cpp

Exits 1 if any answer differs by more than the tolerance.
"""
import heapq
import json
import math
import os
import sys

TOL = 3  # seconds: ION's relative contact times are anchored to when ionadmin ran


def earliest_arrival(contacts, src, dst, t):
    best = {src: t}
    heap = [(t, src)]
    while heap:
        at, node = heapq.heappop(heap)
        if node == dst:
            return at
        if at > best.get(node, math.inf):
            continue
        for c in contacts:
            if c["from"] != node or c["end_s"] <= at:
                continue
            arr = max(at, c["start_s"]) + math.ceil(c["owlt_s"])
            if arr < best.get(c["to"], math.inf):
                best[c["to"]] = arr
                heapq.heappush(heap, (arr, c["to"]))
    return None


def main():
    plan_dir, ion_dir, hdtn_file = sys.argv[1:4]
    contacts = json.load(open(os.path.join(plan_dir, "contacts.json")))["contacts"]
    hdtn = {}
    for line in open(hdtn_file):
        f = line.split()
        if len(f) >= 4:
            hdtn[(int(f[0]), int(f[1]), int(f[2]))] = None if f[3] == "none" else int(f[5])

    bad = 0
    rows = []
    for (src, dst, t) in sorted(hdtn, key=lambda k: (k[0], k[2])):
        want = earliest_arrival(contacts, src, dst, t)
        ion_file = os.path.join(ion_dir, f"ion_{src}_{dst}_{t}.json")
        ion = None
        if os.path.exists(ion_file):
            t0 = int(open(ion_file[:-5] + ".t0").read())
            routes = json.load(open(ion_file)).get("routes", [])
            sel = [r for r in routes if r.get("flag") == 3] or routes
            if sel:
                ion = min(r["deliveryTime"] for r in sel) - t0
        got_h = hdtn[(src, dst, t)]
        ok = lambda v: (v is None and want is None) or (v is not None and want is not None and abs(v - want) <= TOL)
        status = "ok" if ok(ion) and ok(got_h) else "DIFF"
        bad += status != "ok"
        rows.append(f"{src:>4} -> {dst:<4} send {t:>6}  expected {str(want):>6}  ION {str(ion):>6}  HDTN {str(got_h):>6}  {status}")
    print("\n".join(rows))
    print(f"{len(rows)} queries, {bad} differences")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
