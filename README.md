# ✈ 2D Flight Simulator

A physics-based 2D flight simulator built with Python and Pygame.
Model real aerodynamic forces — lift, drag, thrust, and gravity — and
fly an aircraft from takeoff to landing, scored on touchdown quality.

---

## Screenshot

```
┌─────────────────────────────────────────────────────────────────┐
│  ✈ INSTRUMENTS          [gradient sky, clouds, stars at alt]   │
│  AIRSPEED   245.3 kts                                           │
│  ALTITUDE  8 420 ft     ✈──────────────────────────────        │
│  V/SPEED  +1 200 fpm                                           │
│  PITCH       +5.0°       ═══════════════ RUNWAY ═══════════    │
│  THROTTLE   78.0%                                               │
│  FUEL       64.3%                                               │
│  LIFT    62 400 N                                               │
│  DRAG     4 100 N                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features

| Feature | Details |
|---|---|
| **Physics Engine** | Lift, drag, gravity, thrust — all computed per frame using ISA air-density model |
| **Stall Model** | Lift collapses beyond ±25° AoA; stall warning displayed |
| **Fuel System** | Throttle-dependent burn rate; LOW FUEL warning below 15% |
| **Landing Scoring** | Rated on vertical speed, horizontal speed, and pitch at touchdown |
| **Dynamic Sky** | Gradient shifts blue → black with altitude; stars appear above 3 000 m |
| **Parallax Clouds** | Six cloud formations with gentle horizontal drift |
| **Instrument HUD** | Airspeed · Altitude · Vertical Speed · Pitch · Throttle · Fuel · Lift · Drag |
| **Artificial Horizon** | Pitch-animated horizon ball in the HUD panel |
| **Runway** | Marked runway with threshold bars and dashed centreline |
| **Explosion FX** | Frame-animated fireball on crash |
| **Smooth Camera** | Lagged follow-camera keeps the plane in the left-centre of screen |

---

## Controls

| Key | Action |
|---|---|
| `↑` | Pitch up (nose up) |
| `↓` | Pitch down (nose down) |
| `→` | Increase throttle |
| `←` | Decrease throttle |
| `R` | Reset / restart |
| `ESC` | Quit |

---

## Physics Model

```
Lift   L = ½ρv²·Cl·A   (Cl reduced by stall factor above 25° AoA)
Drag   D = ½ρv²·Cd·A
Weight W = m·g
Thrust T = throttle × max_thrust

ax = (T·cos θ − D) / m
ay = (L − W + T·sin θ) / m
```

Air density follows a simplified exponential decay with altitude:

```
ρ(h) = 1.225 · exp(−0.0001 · h)   kg/m³
```

---

## Landing Score

| Metric | Safe threshold |
|---|---|
| Vertical speed | < 3 m/s (~590 fpm) |
| Horizontal speed | < 60 m/s (~117 kts) |
| Pitch | < 10° |

Penalties are deducted for each unit beyond the threshold.
Score < 20 → crash.

| Score | Verdict |
|---|---|
| 90 – 100 | PERFECT LANDING ✈ |
| 70 – 89 | GOOD LANDING |
| 50 – 69 | ROUGH LANDING |
| 20 – 49 | HARD LANDING |
| 0 – 19 | CRASH! |

---

## Project Structure

```
Flight-Simulator/
├── main.py          # Game loop, rendering, HUD, input
├── physics.py       # Aerodynamic force calculations
├── plane.py         # Aircraft state & control methods
├── assets/          # (reserved for custom sprites/sounds)
├── requirements.txt
└── README.md
```

---

## Installation & Running

```bash
# 1. Clone or download the repo
git clone https://github.com/your-username/Flight-Simulator.git
cd Flight-Simulator

# 2. Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch
python main.py
```

Requires **Python 3.10+** and **Pygame 2.5+**.

---

## Tech Stack

- **Python 3.10+**
- **Pygame 2.5** — window, rendering, input, sprite management

---

## Future Ideas

- [ ] Weather / wind effects
- [ ] Multiple aircraft types (glider, fighter, commercial)
- [ ] Instrument Landing System (ILS) glide-slope indicator
- [ ] Matplotlib side-panel with live altitude/speed graphs
- [ ] Waypoint navigation challenge
- [ ] Sound effects (engine, wind, landing)

---

## License

MIT — free to use, modify, and distribute.
