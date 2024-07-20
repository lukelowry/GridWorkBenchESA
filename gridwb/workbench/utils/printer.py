from numpy import pi, zeros

def pmat(matrix, printMat=True):
    '''Helper method to print flaot matricies in more readible format.
    Not reliable. Slow for large matricies. Can definitly be done better with native numpy settings.'''

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



