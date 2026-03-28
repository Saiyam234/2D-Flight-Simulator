"""
plane.py - Aircraft class for 2D Flight Simulator
Holds all aircraft state and delegates physics to physics.py.
"""

import math
from physics import (
    lift_force, drag_force, gravity_force,
    net_vertical_accel, net_horizontal_accel,
    fuel_burn_rate, landing_score,
)

# ── Default aircraft parameters ──────────────────────────────────────────────
AIRCRAFT_DEFAULTS = {
    "mass":        5_000,   # kg
    "wing_area":   50.0,    # m²
    "lift_coeff":  1.5,
    "drag_coeff":  0.03,
    "drag_area":   5.0,     # m²  (fuselage frontal)
    "max_thrust":  80_000,  # N
    "fuel_cap":    5_000,   # kg
    "base_burn":   2.0,     # kg/s at full throttle
}


class Plane:
    """Represents the player's aircraft.

    Coordinate system (world):
        x  → rightward (horizontal)
        y  → upward    (altitude)
    Pixel system inverts y (handled in main.py).
    """

    def __init__(self, x: float, y: float, params: dict | None = None):
        cfg = {**AIRCRAFT_DEFAULTS, **(params or {})}

        # ── Geometry / mass ─────────────────────────────────────────────
        self.mass      = cfg["mass"]
        self.wing_area = cfg["wing_area"]
        self.lift_coeff = cfg["lift_coeff"]
        self.drag_coeff = cfg["drag_coeff"]
        self.drag_area  = cfg["drag_area"]
        self.max_thrust = cfg["max_thrust"]
        self.fuel_cap   = cfg["fuel_cap"]
        self.base_burn  = cfg["base_burn"]

        # ── State ────────────────────────────────────────────────────────
        self.x   = float(x)
        self.y   = float(y)          # altitude in metres
        self.vx  = 0.0               # m/s  horizontal
        self.vy  = 0.0               # m/s  vertical
        self.pitch      = 0.0        # degrees  (+ = nose up)
        self.throttle   = 0.0        # 0.0 – 1.0
        self.fuel       = cfg["fuel_cap"]
        self.on_ground  = True
        self.crashed    = False
        self.landed     = False
        self.landing_result: dict | None = None

        # Controls
        self.pitch_rate = 30.0       # deg/s
        self.throttle_rate = 0.4     # per second

        # Derived for display
        self.lift  = 0.0
        self.drag  = 0.0
        self.thrust = 0.0

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def speed(self) -> float:
        """Total airspeed in m/s."""
        return math.hypot(self.vx, self.vy)

    @property
    def altitude(self) -> float:
        return max(0.0, self.y)

    @property
    def heading_deg(self) -> float:
        """Visual heading from velocity vector (for sprite rotation)."""
        if abs(self.vx) < 0.1 and abs(self.vy) < 0.1:
            return self.pitch
        return math.degrees(math.atan2(self.vy, self.vx))

    @property
    def fuel_pct(self) -> float:
        return self.fuel / self.fuel_cap

    # ── Controls ─────────────────────────────────────────────────────────────

    def increase_throttle(self, dt: float):
        self.throttle = min(1.0, self.throttle + self.throttle_rate * dt)

    def decrease_throttle(self, dt: float):
        self.throttle = max(0.0, self.throttle - self.throttle_rate * dt)

    def pitch_up(self, dt: float):
        self.pitch = min(45.0, self.pitch + self.pitch_rate * dt)

    def pitch_down(self, dt: float):
        self.pitch = max(-45.0, self.pitch - self.pitch_rate * dt)

    # ── Physics step ─────────────────────────────────────────────────────────

    def update(self, dt: float, ground_y: float = 0.0):
        """Advance simulation by dt seconds."""
        if self.crashed or self.landed:
            return

        # ── Fuel ─────────────────────────────────────────────────────────
        if self.fuel > 0:
            burn = fuel_burn_rate(self.throttle, self.base_burn) * dt
            self.fuel = max(0.0, self.fuel - burn)
            effective_throttle = self.throttle
        else:
            effective_throttle = 0.0  # engine out

        # ── Forces ───────────────────────────────────────────────────────
        self.thrust = self.max_thrust * effective_throttle
        self.lift   = lift_force(
            self.speed, self.altitude,
            self.wing_area, self.lift_coeff, self.pitch
        )
        self.drag = drag_force(
            self.speed, self.altitude,
            self.drag_area, self.drag_coeff
        )
        weight = gravity_force(self.mass)

        # ── Accelerations ─────────────────────────────────────────────────
        ax = net_horizontal_accel(self.thrust, self.drag, self.pitch, self.mass)
        ay = net_vertical_accel(self.lift, weight, self.pitch, self.thrust, self.mass)

        # ── Ground constraint ─────────────────────────────────────────────
        if self.on_ground:
            self.vy = 0.0
            ay = max(0.0, ay)               # can only push up
            # rolling friction
            friction = 0.15 if self.throttle < 0.05 else 0.05
            self.vx *= (1.0 - friction * dt * 10)

        # ── Integrate ─────────────────────────────────────────────────────
        self.vx += ax * dt
        self.vy += ay * dt

        # Cap extreme values
        self.vx = max(-400.0, min(400.0, self.vx))
        self.vy = max(-200.0, min(200.0, self.vy))

        self.x += self.vx * dt
        self.y += self.vy * dt

        # ── Ground collision ──────────────────────────────────────────────
        if self.y <= ground_y:
            self.y = ground_y
            if self.vy < -5.0 or self.speed > 120.0:
                if not self.on_ground:
                    self._attempt_landing()
            else:
                self.vy = 0.0
                self.on_ground = True

        else:
            self.on_ground = False

    def _attempt_landing(self):
        result = landing_score(self.vy, self.vx, self.pitch)
        self.landing_result = result
        if result["score"] < 20:
            self.crashed = True
            self.vx = 0.0
            self.vy = 0.0
        else:
            self.landed = True
            self.on_ground = True
            self.vy = 0.0
            self.vx *= 0.3      # braking

    def reset(self, x: float, y: float):
        """Restart the plane from a given position."""
        self.__init__(x, y)
