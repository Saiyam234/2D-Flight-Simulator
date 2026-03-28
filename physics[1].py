"""
physics.py - Aerodynamic physics engine for 2D Flight Simulator
Simulates gravity, lift, drag, and thrust forces.
"""

import math

# ── Physical constants ──────────────────────────────────────────────────────
GRAVITY          = 9.81        # m/s²
AIR_DENSITY      = 1.225       # kg/m³  (sea-level ISA)
AIR_DENSITY_SCALE = 0.0001     # density falloff with altitude (simplified)

# ── Force calculations ───────────────────────────────────────────────────────

def air_density(altitude_m: float) -> float:
    """Return air density that decreases with altitude."""
    return AIR_DENSITY * math.exp(-AIR_DENSITY_SCALE * altitude_m)


def lift_force(speed: float, altitude: float, wing_area: float,
               lift_coeff: float, pitch_deg: float) -> float:
    """
    L = 0.5 * rho * v² * Cl * A
    Pitch angle modifies effective AoA.  Beyond ±25° the wing stalls.
    """
    rho = air_density(altitude)
    aoa = pitch_deg                          # simplified: AoA ≈ pitch
    stall_angle = 25.0
    if abs(aoa) > stall_angle:
        stall_factor = max(0.0, 1.0 - (abs(aoa) - stall_angle) / 15.0)
    else:
        stall_factor = 1.0
    effective_cl = lift_coeff * math.sin(math.radians(aoa * 2)) * stall_factor
    return 0.5 * rho * speed ** 2 * effective_cl * wing_area


def drag_force(speed: float, altitude: float, drag_area: float,
               drag_coeff: float) -> float:
    """D = 0.5 * rho * v² * Cd * A"""
    rho = air_density(altitude)
    return 0.5 * rho * speed ** 2 * drag_coeff * drag_area


def gravity_force(mass: float) -> float:
    """W = m * g"""
    return mass * GRAVITY


def net_vertical_accel(lift: float, weight: float, pitch_deg: float,
                       thrust: float, mass: float) -> float:
    """
    Vertical component of all forces divided by mass.
    Thrust has a vertical component based on pitch.
    """
    thrust_vertical = thrust * math.sin(math.radians(pitch_deg))
    net = lift - weight + thrust_vertical
    return net / mass


def net_horizontal_accel(thrust: float, drag: float,
                         pitch_deg: float, mass: float) -> float:
    """
    Horizontal component: thrust*cos(pitch) - drag.
    """
    thrust_horizontal = thrust * math.cos(math.radians(pitch_deg))
    net = thrust_horizontal - drag
    return net / mass


def fuel_burn_rate(throttle: float, base_burn: float) -> float:
    """Fuel consumed per second = throttle * base burn rate."""
    return throttle * base_burn


def landing_score(vertical_speed: float, horizontal_speed: float,
                  pitch_deg: float) -> dict:
    """
    Evaluate landing quality.
    Returns a dict with score (0-100) and verdict string.
    """
    # Safe thresholds
    SAFE_VERT  = 3.0    # m/s
    SAFE_HORIZ = 60.0   # m/s
    SAFE_PITCH = 10.0   # degrees

    v_pen   = max(0.0, abs(vertical_speed)  - SAFE_VERT)
    h_pen   = max(0.0, abs(horizontal_speed) - SAFE_HORIZ)
    p_pen   = max(0.0, abs(pitch_deg)        - SAFE_PITCH)

    score = 100 - (v_pen * 10 + h_pen * 0.5 + p_pen * 2)
    score = max(0, min(100, int(score)))

    if score >= 90:
        verdict = "PERFECT LANDING! ✈"
    elif score >= 70:
        verdict = "GOOD LANDING"
    elif score >= 50:
        verdict = "ROUGH LANDING"
    elif score >= 20:
        verdict = "HARD LANDING — check for damage"
    else:
        verdict = "CRASH!"

    return {"score": score, "verdict": verdict}
