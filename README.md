# mars-contact-plan

Contact plans for a Mars relay network, computed from orbital geometry: when a relay
orbiter can talk to rovers or landers on the surface, when it can talk to Earth, and the
light time on each link. The output loads directly into DTN implementations as a contact
plan for contact graph routing.

- **Surface site <-> orbiter**: the orbiter is above the site's elevation mask, as Mars turns.
- **Orbiter <-> Earth**: Mars is not between the orbiter and Earth, and at least one Deep
  Space Network station (Goldstone, Madrid, Canberra) has Mars above its elevation mask.
- **Light time**: the Earth-Mars distance at the time of each contact.

Pure Python standard library, no dependencies.

## Usage

```bash
python -m marsplan --start 2027-02-19T00:00:00Z --hours 24.66 \
    --orbit 255x320/92.7 --site rover:200:18.44:77.45 --out plans/
```

```
orbit 255 x 320 km, i=92.7 deg, period 112.8 min
Earth-Mars one-way light time at start: 5.64 min
  orbiter->Earth         +  0.00 h   64.2 min  owlt  338.304 s  Madrid
  rover->orbiter         +  0.76 h   10.0 min  owlt    0.003 s
  orbiter->Earth         +  1.39 h   93.8 min  owlt  338.297 s  Goldstone+Madrid
  ...
```

| Option | Meaning |
| --- | --- |
| `--start` | UTC start time |
| `--hours` | plan length (24.66 h is one sol) |
| `--step` | time step in seconds (default 20) |
| `--orbit` | `periapsis x apoapsis altitude / inclination`, km and degrees (default MRO-like `255x320/92.7`) |
| `--raan` | longitude of the orbit's ascending node on the Mars equator, degrees |
| `--site` | `name:node:latitude:east longitude`, repeatable (default Jezero crater) |
| `--orbiter-node`, `--earth-node` | ipn node numbers (default 100 and 1) |
| `--out` | directory for the plan files |

Output files:

- `ion.rc`: `a contact` and `a range` lines for ionadmin (rates in bytes per second, ranges
  in whole seconds of light time)
- `hdtn.json`: an HDTN contact plan (rates in bits per second)
- `contacts.json`: every contact with its duration, light time and the DSN stations in view

## Model

- Earth and Mars positions from JPL's approximate Keplerian elements (Standish, valid
  1800-2050). Errors are far below what matters for contact windows or light time.
- Mars orientation from the IAU WGCCRE 2015 model.
- The orbiter is a Keplerian orbit with the secular drift of its node and argument of
  periapsis from Mars' J2.
- Not modelled: terrain masking, link budgets, the Sun near the line of sight (solar
  conjunction), and Earth's precession since J2000 (about 0.4 degrees).

## Checks

```bash
python -m unittest discover tests
```

The tests compare against independently known values: the 2020-10-06 Earth-Mars close
approach (62.07 million km), the 3 to 22 minute range of one-way light time, Mars'
sidereal day, the period of an MRO-like orbit (about 112 minutes), pass counts and lengths
over a surface site, and occultation by Mars at the grazing angle.
