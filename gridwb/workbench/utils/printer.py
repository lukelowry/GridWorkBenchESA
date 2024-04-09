import cmath
from .altsol import cpower
from numpy import pi, zeros

def pmat(matrix, printMat=True):
    def cstr(c):
        rV = round(c.real,2)
        iV = round(c.imag,2)

        if rV ==0 and iV==0:
            return '0'
        if rV == 0:
            if iV < 0:
                return f'-j{-iV}' 
            return f'j{iV}'
        if iV == 0:
            return f'{rV}'
        if iV < 0:
            return f'{rV} -j{-iV}' 
        return f'{rV} + j{iV}'

    colwidth = zeros(len(matrix[0]))
    for i in range(len(matrix[0])):
        for j in range(len(matrix)):
            colwidth[i] = max(len(cstr(matrix[j][i])), colwidth[i])
    
    prints = ""

    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            s = cstr(matrix[i][j])
            spaces = int(colwidth[j]-len(s)) + 3
            prints += s + " "*spaces
        prints += '\n'

    if printMat:
        print(prints)
    else:
        return prints

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
