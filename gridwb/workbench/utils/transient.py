from pandas import DataFrame


def end(meta: DataFrame, data: DataFrame) -> DataFrame:
    t = data.tail(1).reset_index(drop=True).copy()
    t.index = ["Value"]
    return (meta, t)
