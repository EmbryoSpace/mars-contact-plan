"""A relay orbiter around Mars: Keplerian orbit with the secular J2 drift of the node and
argument of periapsis. Elements are relative to the Mars equator, with the node measured
from the ascending node of the Mars equator on the ICRF equator (the IAU frame's Q axis).
"""
import math
from dataclasses import dataclass

from .ephemeris import MARS_GM, MARS_RADIUS_KM, mars_pole_and_meridian

MARS_J2 = 1.96045e-3


@dataclass
class Orbit:
    periapsis_alt_km: float
    apoapsis_alt_km: float
    inclination_deg: float
    raan_deg: float = 0.0
    arg_periapsis_deg: float = 0.0
    mean_anomaly_deg: float = 0.0
    epoch_jd: float = 0.0

    @property
    def a_km(self):
        return MARS_RADIUS_KM + (self.periapsis_alt_km + self.apoapsis_alt_km) / 2

    @property
    def e(self):
        rp = MARS_RADIUS_KM + self.periapsis_alt_km
        ra = MARS_RADIUS_KM + self.apoapsis_alt_km
        return (ra - rp) / (ra + rp)

    @property
    def mean_motion_rad_s(self):
        return math.sqrt(MARS_GM / self.a_km ** 3)

    @property
    def period_s(self):
        return 2 * math.pi / self.mean_motion_rad_s

    def j2_rates_rad_s(self):
        """Secular drift of the node and argument of periapsis due to J2."""
        n, a, e = self.mean_motion_rad_s, self.a_km, self.e
        i = math.radians(self.inclination_deg)
        f = 1.5 * MARS_J2 * (MARS_RADIUS_KM / (a * (1 - e * e))) ** 2 * n
        return -f * math.cos(i), f * (2 - 2.5 * math.sin(i) ** 2)

    def position(self, jd):
        """Orbiter position relative to Mars' centre, km, ICRF."""
        dt = (jd - self.epoch_jd) * 86400.0
        draan, dargp = self.j2_rates_rad_s()
        raan = math.radians(self.raan_deg) + draan * dt
        argp = math.radians(self.arg_periapsis_deg) + dargp * dt
        m = math.radians(self.mean_anomaly_deg) + self.mean_motion_rad_s * dt
        e = self.e
        ea = m
        for _ in range(50):
            d = (ea - e * math.sin(ea) - m) / (1 - e * math.cos(ea))
            ea -= d
            if abs(d) < 1e-12:
                break
        xp = self.a_km * (math.cos(ea) - e)
        yp = self.a_km * math.sqrt(1 - e * e) * math.sin(ea)
        i = math.radians(self.inclination_deg)
        cw, sw, co, so, ci, si = math.cos(argp), math.sin(argp), math.cos(raan), math.sin(raan), math.cos(i), math.sin(i)
        # orbital plane -> Mars equatorial inertial frame (q along the node, z along the pole)
        q = (cw * co - sw * so * ci) * xp + (-sw * co - cw * so * ci) * yp
        r = (cw * so + sw * co * ci) * xp + (-sw * so + cw * co * ci) * yp
        s = (sw * si) * xp + (cw * si) * yp
        _, z, node, m_axis = mars_pole_and_meridian(jd)
        return tuple(q * node[k] + r * m_axis[k] + s * z[k] for k in range(3))
