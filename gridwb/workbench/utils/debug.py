
from gridwb.saw import SAW
from gridwb.workbench.grid.components import GObject

def problemField(esa: SAW, g: GObject, keys):
    '''Find the field(s) that cause a download issue'''

    problematic = []
    good = []
    exceptions = []
    for f in g.fields:
        if f not in keys:
            try:
                r = esa.GetParametersMultipleElement(g.TYPE, keys+[f])
                good += [f]
            except Exception as e:
                problematic += [f]
                exceptions += [e]

    print("The following fields caused issues:")
    print(problematic)

    print("These fields had no issues:")
    print(good)
    
    print("Exceptions Thrown:")
    for e in exceptions:
        print(e)


