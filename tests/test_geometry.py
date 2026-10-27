"""Checks against independently known values.  python -m unittest discover tests"""
import math
import unittest
from datetime import datetime, timezone

from marsplan.contacts import Site, compute
from marsplan.ephemeris import (AU_KM, earth_mars_km, julian_date, mars_surface_point, norm,
                                one_way_light_time_s)
from marsplan.orbit import Orbit


def jd(s):
    return julian_date(datetime.fromisoformat(s).replace(tzinfo=timezone.utc))


class Ephemeris(unittest.TestCase):
    def test_2020_close_approach(self):
        # Closest approach 2020-10-06: 62.07 million km (0.4149 au)
        d = norm(earth_mars_km(jd("2020-10-06T14:18:00")))
        self.assertAlmostEqual(d / 1e6, 62.07, delta=0.6)

    def test_light_time_range(self):
        # Over a synodic period the one-way light time stays within about 3 to 22.5 minutes
        lo, hi = math.inf, 0
        start = jd("2020-01-01T00:00:00")
        for k in range(0, 800, 2):
            t = one_way_light_time_s(start + k) / 60
            lo, hi = min(lo, t), max(hi, t)
        self.assertGreater(lo, 3.0)
        self.assertLess(lo, 4.0)
        self.assertGreater(hi, 21.0)
        self.assertLess(hi, 22.6)

    def test_mars_sidereal_day(self):
        # A surface point returns to the same inertial direction after one sidereal day
        # (88642.663 s); one solar sol (88775.244 s) is not enough
        t0 = jd("2027-01-01T00:00:00")
        p0, _ = mars_surface_point(18.44, 77.45, t0)
        p1, _ = mars_surface_point(18.44, 77.45, t0 + 88642.663 / 86400)
        p2, _ = mars_surface_point(18.44, 77.45, t0 + 88775.244 / 86400)
        self.assertLess(norm(tuple(p0[k] - p1[k] for k in range(3))), 1.0)
        self.assertGreater(norm(tuple(p0[k] - p2[k] for k in range(3))), 20.0)


class Relay(unittest.TestCase):
    def test_mro_like_period(self):
        # MRO's science orbit (about 255 x 320 km) has a period of about 112 minutes
        self.assertAlmostEqual(Orbit(255, 320, 92.7).period_s / 60, 112, delta=2)

    def test_daily_passes(self):
        # A polar low orbiter passes over a site a few times a sol, each pass several minutes long
        t = jd("2027-02-19T00:00:00")
        o = Orbit(255, 320, 92.7, epoch_jd=t)
        cs = compute(t, 24.6 * 3600, 10, o, 100, 1, [Site("rover", 200, 18.44, 77.45)])
        passes = [c for c in cs if (c.a, c.b) == (200, 100)]
        self.assertGreaterEqual(len(passes), 2)
        self.assertLessEqual(len(passes), 8)
        for p in passes:
            self.assertGreater(p.end - p.start, 60)
            self.assertLess(p.end - p.start, 20 * 60)
            self.assertLess(p.owlt_s, 0.02)  # a few thousand km at most

    def test_earth_contacts_use_mars_light_time(self):
        t = jd("2027-02-19T00:00:00")
        o = Orbit(255, 320, 92.7, epoch_jd=t)
        cs = compute(t, 24 * 3600, 20, o, 100, 1, [Site("rover", 200, 18.44, 77.45)])
        earth = [c for c in cs if (c.a, c.b) == (100, 1)]
        self.assertTrue(earth)
        owlt = one_way_light_time_s(t)
        for c in earth:
            self.assertAlmostEqual(c.owlt_s, owlt, delta=2.0)
        # Gaps (Mars in the way, or no station sees Mars) never last longer than one orbit
        gaps = [b.start - a.end for a, b in zip(earth, earth[1:])]
        self.assertTrue(all(g < o.period_s for g in gaps))

    def test_occultation(self):
        from marsplan.contacts import _occulted_by_mars
        r = 3689.5  # 300 km altitude
        self.assertTrue(_occulted_by_mars((r, 0, 0), (-1, 0, 0)))      # Earth straight behind Mars
        self.assertFalse(_occulted_by_mars((r, 0, 0), (1, 0, 0)))      # Earth straight ahead
        self.assertFalse(_occulted_by_mars((0, 0, r), (1, 0, 0)))      # Earth beside the orbiter
        # Grazing: at angle phi from the anti-Earth point the line of sight passes r*sin(phi)
        # from Mars' centre, so it clears Mars once sin(phi) > 3389.5/3689.5 (phi > 66.7 deg)
        ang = math.radians(67.0)
        self.assertFalse(_occulted_by_mars((r * math.cos(ang), r * math.sin(ang), 0), (-1, 0, 0)))
        ang = math.radians(66.4)
        self.assertTrue(_occulted_by_mars((r * math.cos(ang), r * math.sin(ang), 0), (-1, 0, 0)))


if __name__ == "__main__":
    unittest.main()
