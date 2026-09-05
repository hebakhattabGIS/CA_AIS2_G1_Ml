'''
this module applys the following data processing steps 
on the dataset and columns defined in the config file
Data preprocessing steps:
1- read data
2- check dtypes 
3- handle dtype 
4- check nulls
5- handling nulls
6- check outliers
7- handling outliers
8- check duplicated
9- handling duplicated
10- data visualization
11- data splitting [??]
12- Normalization [scaling of data, smoothing]
13- encoding 
'''
import config.config as cnf
import preprocessing  
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")

if __name__ == "__main__":
    #read the dataset
    
    df = preprocessing.Read_data_file(cnf.fpath)
    print(f"the raw data: \n {df}")

    #drop unnecessary features -no columns to drop in this dataset
    #df = Drop_unnecessary_features(df,COLS_TO_DROP)
    #print(f"dataset after removing unnecessary features: \n {df}")

    #listing datatypes and unique features
    dt = preprocessing.Check_data_type(df)
    print(f"data types in the dataset: \n {dt}")

    #handling datatypes, category 
    df = preprocessing.define_category_features(df, cnf.CAT_COLS)
    print(f"after handling category data in the dataset: \n {df.dtypes}")

    #handling nulls
    preprocessing.check_nulls(df)
    #print(f"checking nulls in the dataset: \n {df}")

    #check outliers & print fences and outliers
    preprocessing.check_outliers(df)

    #replace outliers values?

    #check duplicates
    x= df.duplicated().sum()
    print(f"duplicates: {x}")
    if x>0:
        df = preprocessing.removeduplicate(df)
        print(f"{x} duplicates was removed")
    

