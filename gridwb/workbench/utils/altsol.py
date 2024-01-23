import numpy as np
import quaternion
import cmath


# Formats Complex Phasor as Quaternion
def quat(a, b):
    return np.quaternion(0, a, b, 0)


# HV/LV Conversion
def lv(v, e) -> complex:
    vq = np.quaternion(0, v.real, v.imag, 0)
    eq = np.quaternion(0, e.real, e.imag, 0)
    eqt = np.quaternion(0, -e.imag, e.real, 0) / np.abs(e)

    c = vq + eq / 2
    rot = eqt.conjugate() * c * eqt
    lv = rot - eq / 2

    return lv.x + lv.y * 1j


def altsols(volts, ybus) -> list[complex]:
    alts = []
    eps = []

    # Calc Epsilon Values Per Bus
    for i in range(len(volts)):
        vy = np.multiply(ybus[i], volts)
        m = vy / ybus[i][i]
        e = sum(np.delete(m, i))
        eps += [e]

    # Calculate Alt Solutions
    for v, e in zip(volts, eps):
        alts += [lv(v, e)]

    return alts


def cpower(volts, ybus) -> list[complex]:
    sAll = []

    for v, yrow in zip(volts, ybus):
        vy = np.multiply(yrow, volts)
        s = sum(v.conjugate() * vy).conjugate()
        sAll.append(s)

    return sAll
