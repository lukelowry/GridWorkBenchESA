import cmath
from .altsol import cpower
from numpy import pi


def printpow(volts, ybus, base=100):
    slist = cpower(volts, ybus)

    for i, s in enumerate(slist):
        print(f"Bus {i+1}\t", end="")
        print(f"P: {round(s.real*base)} MW\t", end="")
        print(f"Q: {round(s.imag*base)} MVAR")

    print()


def printvolts(vlist):
    for i, v in enumerate(vlist):
        polarv = cmath.polar(v)
        print(f"Bus {i+1}\t", end="")
        print(f"|V|: {round(polarv[0],4)}\t", end="")
        print(f"\u03B8: {round(polarv[1]*180/pi,4)}\u00B0")

    print()


def printsol(volts, ybus, base=100):
    printvolts(volts)
    printpow(volts, ybus)
