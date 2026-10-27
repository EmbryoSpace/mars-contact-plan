"""Approximate positions of Earth and Mars, and the frames needed for Mars relay geometry.

Planet positions use the Keplerian elements and rates of E. M. Standish, "Keplerian
Elements for Approximate Positions of the Major Planets" (JPL, table 1, valid
1800-2050). Errors are a few hundred arcseconds at most, far below what matters for
contact windows (minutes) or light time (milliseconds of a 3-22 minute delay).

Mars orientation uses the IAU WGCCRE 2015 model (Archinal et al. 2018).
All vectors are in kilometres, in the ICRF/J2000 equatorial frame unless noted.
"""
import math

AU_KM = 149_597_870.7
C_KM_S = 299_792.458
OBLIQUITY_J2000 = math.radians(23.43928)
MARS_RADIUS_KM = 3389.5
EARTH_RADIUS_KM = 6378.137
MARS_GM = 42_828.37  # km^3/s^2

# Standish table 1: a [au], e, I [deg], L [deg], long. peri [deg], long. node [deg],
# each followed by its rate per Julian century.
ELEMENTS = {
    "earth": ((1.00000261, 0.00000562), (0.01671123, -0.00004392), (-0.00001531, -0.01294668),
              (100.46457166, 35999.37244981), (102.93768193, 0.32327364), (0.0, 0.0)),
    "mars": ((1.52371034, 0.00001847), (0.09339410, 0.00007882), (1.84969142, -0.00813131),
             (-4.55343205, 19140.30268499), (-23.94362959, 0.44441088), (49.55953891, -0.29257343)),
}


def julian_date(t):
    """Julian date (UTC treated as TT; the 69 s difference is irrelevant here) of a datetime."""
    return t.timestamp() / 86400.0 + 2440587.5


def _solve_kepler(m, e):
    ea = m if e < 0.8 else math.pi
    for _ in range(50):
        d = (ea - e * math.sin(ea) - m) / (1 - e * math.cos(ea))
        ea -= d
        if abs(d) < 1e-12:
            break
    return ea


def heliocentric(planet, jd):
    """Heliocentric position of a planet, ICRF equatorial, km."""
    t = (jd - 2451545.0) / 36525.0
    (a, da), (e, de), (i, di), (l, dl), (w, dw), (o, do) = ELEMENTS[planet]
    a, e = a + da * t, e + de * t
    i, l, w, o = (math.radians(x + dx * t) for x, dx in ((i, di), (l, dl), (w, dw), (o, do)))
    arg_peri = w - o
    m = math.remainder(l - w, 2 * math.pi)
    ea = _solve_kepler(m, e)
    xp = a * (math.cos(ea) - e)
    yp = a * math.sqrt(1 - e * e) * math.sin(ea)
    # orbital plane -> ecliptic
    cw, sw, co, so, ci, si = math.cos(arg_peri), math.sin(arg_peri), math.cos(o), math.sin(o), math.cos(i), math.sin(i)
    x = (cw * co - sw * so * ci) * xp + (-sw * co - cw * so * ci) * yp
    y = (cw * so + sw * co * ci) * xp + (-sw * so + cw * co * ci) * yp
    z = (sw * si) * xp + (cw * si) * yp
    # ecliptic -> equatorial
    ce, se = math.cos(OBLIQUITY_J2000), math.sin(OBLIQUITY_J2000)
    return (x * AU_KM, (y * ce - z * se) * AU_KM, (y * se + z * ce) * AU_KM)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(a):
    return math.sqrt(dot(a, a))


def unit(a):
    n = norm(a)
    return (a[0] / n, a[1] / n, a[2] / n)


def earth_mars_km(jd):
    """Earth to Mars vector (km, equatorial)."""
    return sub(heliocentric("mars", jd), heliocentric("earth", jd))


def one_way_light_time_s(jd):
    return norm(earth_mars_km(jd)) / C_KM_S


# ---- Mars body frame (IAU 2015) ---------------------------------------------------------

def mars_pole_and_meridian(jd):
    """Unit vectors of Mars' body-fixed x (prime meridian) and z (north pole) axes, ICRF."""
    d = jd - 2451545.0
    t = d / 36525.0
    ra = math.radians(317.269202 - 0.10927547 * t)
    dec = math.radians(54.432516 - 0.05827105 * t)
    w = math.radians((176.049863 + 350.891982443297 * d) % 360.0)
    z = (math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec))
    # node of the Mars equator on the ICRF equator
    n = unit((-math.sin(ra), math.cos(ra), 0.0))
    m = (z[1] * n[2] - z[2] * n[1], z[2] * n[0] - z[0] * n[2], z[0] * n[1] - z[1] * n[0])
    x = tuple(math.cos(w) * n[k] + math.sin(w) * m[k] for k in range(3))
    return x, z, n, m


def mars_surface_point(lat_deg, lon_deg_east, jd):
    """Position of a point on the Mars surface relative to Mars' centre (km, ICRF), and its up vector."""
    x, z, _, _ = mars_pole_and_meridian(jd)
    y = (z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0])
    la, lo = math.radians(lat_deg), math.radians(lon_deg_east)
    up = tuple(math.cos(la) * math.cos(lo) * x[k] + math.cos(la) * math.sin(lo) * y[k] + math.sin(la) * z[k]
               for k in range(3))
    return tuple(MARS_RADIUS_KM * u for u in up), up


# ---- Earth ---------------------------------------------------------------------------

def gmst_rad(jd):
    """Greenwich mean sidereal time (IAU 1982), radians."""
    t = (jd - 2451545.0) / 36525.0
    s = 280.46061837 + 360.98564736629 * (jd - 2451545.0) + 0.000387933 * t * t
    return math.radians(s % 360.0)


def earth_station_up(lat_deg, lon_deg_east, jd):
    """Local vertical of an Earth station (ICRF, ignoring precession since J2000)."""
    la = math.radians(lat_deg)
    lst = gmst_rad(jd) + math.radians(lon_deg_east)
    return (math.cos(la) * math.cos(lst), math.cos(la) * math.sin(lst), math.sin(la))


def elevation_deg(up, direction):
    return math.degrees(math.asin(max(-1.0, min(1.0, dot(up, unit(direction))))))
