"""Compute a DTN contact plan for a Mars relay orbiter, surface sites and Earth.

  python -m marsplan --start 2027-02-19T00:00:00Z --hours 24 \
      --orbit 255x320/92.7 --site rover:200:18.44:77.45 --out plans/

Writes ion.rc (ionadmin), hdtn.json (HDTN contact plan) and contacts.json, and prints a
summary. Nodes: Earth 1, orbiter 100, sites as given (name:node:lat:lon_east).
"""
import argparse
import os
from datetime import datetime, timezone

from . import writers
from .contacts import Site, compute
from .ephemeris import julian_date, one_way_light_time_s
from .orbit import Orbit


def parse_orbit(s):
    alts, _, inc = s.partition("/")
    peri, _, apo = alts.partition("x")
    return Orbit(float(peri), float(apo or peri), float(inc or 92.7))


def parse_site(s):
    name, node, lat, lon = s.split(":")
    return Site(name, int(node), float(lat), float(lon))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", required=True, help="UTC start, e.g. 2027-02-19T00:00:00Z")
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--step", type=float, default=20.0, help="time step in seconds")
    ap.add_argument("--orbit", default="255x320/92.7", help="periapsis x apoapsis altitude km / inclination deg")
    ap.add_argument("--raan", type=float, default=0.0)
    ap.add_argument("--site", action="append", default=[], help="name:node:lat:lon_east (repeatable)")
    ap.add_argument("--orbiter-node", type=int, default=100)
    ap.add_argument("--earth-node", type=int, default=1)
    ap.add_argument("--out", default=None, help="directory for ion.rc, hdtn.json, contacts.json")
    a = ap.parse_args()

    start = datetime.fromisoformat(a.start.replace("Z", "+00:00")).astimezone(timezone.utc)
    jd = julian_date(start)
    orbit = parse_orbit(a.orbit)
    orbit.raan_deg, orbit.epoch_jd = a.raan, jd
    sites = [parse_site(s) for s in a.site] or [Site("rover", 200, 18.44, 77.45)]  # Jezero crater
    contacts = compute(jd, a.hours * 3600, a.step, orbit, a.orbiter_node, a.earth_node, sites)

    print(f"orbit {orbit.periapsis_alt_km:.0f} x {orbit.apoapsis_alt_km:.0f} km, i={orbit.inclination_deg} deg, "
          f"period {orbit.period_s / 60:.1f} min")
    print(f"Earth-Mars one-way light time at start: {one_way_light_time_s(jd) / 60:.2f} min")
    for c in contacts:
        if c.a < c.b or c.a == a.earth_node:
            continue
    shown = [c for c in contacts if (c.a, c.b) in {(s.node, a.orbiter_node) for s in sites} | {(a.orbiter_node, a.earth_node)}]
    for c in shown:
        kind = "orbiter->Earth" if c.b == a.earth_node else f"{c.via}->orbiter"
        print(f"  {kind:22s} +{c.start / 3600:6.2f} h  {(c.end - c.start) / 60:5.1f} min  owlt {c.owlt_s:8.3f} s  {c.via if c.b == a.earth_node else ''}")
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "ion.rc"), "w") as f:
            f.write(writers.ion(contacts))
        with open(os.path.join(a.out, "hdtn.json"), "w") as f:
            f.write(writers.hdtn(contacts))
        with open(os.path.join(a.out, "contacts.json"), "w") as f:
            f.write(writers.plain(contacts, start.isoformat()))
        print(f"wrote {a.out}/ion.rc, hdtn.json, contacts.json ({len(contacts)} contacts)")


if __name__ == "__main__":
    main()
