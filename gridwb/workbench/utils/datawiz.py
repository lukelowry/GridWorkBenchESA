
from typing import Callable
from pandas import DataFrame, MultiIndex


def flat(meta: DataFrame, data: DataFrame, copy=True) -> DataFrame:

    if copy:
        flatData = data.copy()
        flatData.columns = MultiIndex.from_frame(meta.copy())
    else:
        flatData = data
        flatData.columns = MultiIndex.from_frame(meta)

    return flatData.T.reset_index()

def select(df: DataFrame, cols: list[str], newcols: list[str] = None) -> DataFrame:

    # Get Cols & Copy
    sel = df[cols].copy()

    # Rename if Needed
    if newcols:
        sel.columns = newcols

    # Freshen index 
    sel.reset_index(drop=True, inplace=True)

    return sel

# Add Fields to Data Frame
def addFields(df: DataFrame, mapper: Callable[[str],object], fields: list[str], copy=True) -> DataFrame:

    if copy:
        df = df.copy()

    fieldVals = {f: [] for f in fields}

    # Mapper Keys are fields in the given DF
    # Mapper Values are functions to retrieve a respective object to aquire field data
    for i in df.index:
        o = mapper(df.loc[i])
        for f in fields:
            fieldVals[f].append(getattr(o, f))

    for f in fields:
        df[f] = fieldVals[f]

    return df

def dropFields(df: DataFrame, fields: list[str] | str):

    if not isinstance(fields, list):
        fields = [fields]

    try:
        df.drop(columns=fields, inplace=True)
    except KeyError:
        print('Field DNE, no change made.')
    


