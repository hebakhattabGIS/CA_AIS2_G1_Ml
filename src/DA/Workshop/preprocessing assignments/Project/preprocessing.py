import pandas as pd

#read the dataset
def Read_data_file(file_path)->pd.DataFrame:
    try:
        df = pd.read_csv(file_path)
        return df 
    except FileNotFoundError:
        raise FileNotFoundError (f"file does not exist: {file_path}")

    except pd.errors.EmptyDataError:
        raise ValueError(f"file is empty or cannot be read: {file_path}")

    except Exception as e:
        raise ValueError(f"unexpected error wile reading the file: {e}")


#remove unnecessary features
def Drop_unnecessary_features(df: pd.DataFrame, cols_to_drop: list[str])->pd.DataFrame:

    return df.drop(columns=cols_to_drop)

#check data type &
def Check_data_type(df: pd.DataFrame):
    dtype = df.dtypes
    n_uniq = df.nunique()
    return pd.DataFrame({"Dtype ": dtype, "N_unique ": n_uniq}).T

