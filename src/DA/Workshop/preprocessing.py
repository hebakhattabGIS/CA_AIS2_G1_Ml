import pandas as pd
def drop_cols(df: pd.DataFrame, cols: list[str])->pd.DataFrame:
    return df.drop(columns=cols)

def get_data_summary(df):
    return pd.DataFrame({"Dtype ":df.dtype, "N_unique ": df.n_uniq}).T