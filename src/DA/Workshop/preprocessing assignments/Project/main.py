from Config.config import COLS_TO_DROP
from preprocessing import Read_data_file, Drop_unnecessary_features, Check_data_type 
import pandas as pd


if __name__ == "__main__":
    #read the dataset
    fpath = r".\Data\raw\Titanic.csv"
    df = Read_data_file(fpath)
    print(f"the raw data: \n {df}")

    #drop unnecessary features
    df = Drop_unnecessary_features(df,COLS_TO_DROP)
    print(f"dataset after removing unnecessary features: \n {df}")

    #listing datatypes and unique features
    df = Check_data_type(df)
    print(f"data types in the dataset: \n {df}")
