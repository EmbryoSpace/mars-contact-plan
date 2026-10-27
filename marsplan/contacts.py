"""Contact windows for a Mars relay: surface sites <-> orbiter, orbiter <-> Earth."""
import math
from dataclasses import dataclass, field

from .ephemeris import (C_KM_S, MARS_RADIUS_KM, dot, earth_mars_km, earth_station_up, elevation_deg,
                        mars_surface_point, norm, one_way_light_time_s, sub, unit)


@dataclass
class Site:
    name: str
    node: int
    lat_deg: float
    lon_deg_east: float
    min_elevation_deg: float = 10.0
    rate_bps: int = 2_000_000


@dataclass
class Station:
    name: str
    lat_deg: float
    lon_deg_east: float
    min_elevation_deg: float = 10.0


@dataclass
class Contact:
    a: int
    b: int
    start: float  # seconds from the plan start
    end: float
    rate_bps: int
    owlt_s: float
    via: str = ""
    extra: dict = field(default_factory=dict)


DSN = [
    Station("Goldstone", 35.4267, -116.8900),
    Station("Madrid", 40.4314, -4.2481),
    Station("Canberra", -35.4014, 148.9817),
]


def _occulted_by_mars(point, direction):
    """Does the ray from `point` (Mars-centred, km) along `direction` hit Mars?"""
    d = unit(direction)
    t = -dot(point, d)
    if t <= 0:
        return False
    closest = tuple(point[k] + t * d[k] for k in range(3))
    return norm(closest) < MARS_RADIUS_KM


def windows(times, visible):
    """Turn per-step visibility into (start, end) windows."""
    out, start = [], None
    for t, v in zip(times, visible):
        if v and start is None:
            start = t
        elif not v and start is not None:
            out.append((start, t))
            start = None
    if start is not None:
        out.append((start, times[-1]))
    return out


def compute(start_jd, duration_s, step_s, orbit, orbiter_node, earth_node, sites, stations=DSN,
            earth_rate_bps=500_000, min_window_s=60):
    times = [k * step_s for k in range(int(duration_s // step_s) + 1)]
    jds = [start_jd + t / 86400.0 for t in times]
    contacts = []

    # Surface site <-> orbiter
    for site in sites:
        vis, ranges = [], []
        for jd in jds:
            pos = orbit.position(jd)
            ground, up = mars_surface_point(site.lat_deg, site.lon_deg_east, jd)
            los = sub(pos, ground)
            vis.append(elevation_deg(up, los) >= site.min_elevation_deg)
            ranges.append(norm(los))
        for s, e in windows(times, vis):
            if e - s < min_window_s:
                continue
            i0, i1 = times.index(s), times.index(e)
            owlt = max(ranges[i0:i1 + 1]) / C_KM_S
            for a, b in ((site.node, orbiter_node), (orbiter_node, site.node)):
                contacts.append(Contact(a, b, s, e, site.rate_bps, owlt, via=site.name))

    # Orbiter <-> Earth (any station that sees Mars, orbiter not behind Mars)
    vis, best = [], []
    for jd in jds:
        pos = orbit.position(jd)
        to_earth = sub((0, 0, 0), earth_mars_km(jd))  # Mars -> Earth
        seen_by = [st.name for st in stations
                   if elevation_deg(earth_station_up(st.lat_deg, st.lon_deg_east, jd), earth_mars_km(jd))
                   >= st.min_elevation_deg]
        vis.append(bool(seen_by) and not _occulted_by_mars(pos, to_earth))
        best.append(seen_by)
    for s, e in windows(times, vis):
        if e - s < min_window_s:
            continue
        i0, i1 = times.index(s), times.index(e)
        owlt = max(one_way_light_time_s(jds[i]) for i in (i0, i1))
        stations_used = sorted({n for i in range(i0, i1) for n in best[i]})
        for a, b in ((orbiter_node, earth_node), (earth_node, orbiter_node)):
            contacts.append(Contact(a, b, s, e, earth_rate_bps, owlt, via="+".join(stations_used)))

    contacts.sort(key=lambda c: (c.start, c.a, c.b))
    return contacts
