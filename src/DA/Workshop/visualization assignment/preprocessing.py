import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")
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

#handle Category columns
def define_category_features(df: pd.DataFrame, cols_to_cat: list[str])->pd.DataFrame:
    columns = cols_to_cat
    df[columns] =df[columns].astype("category")
    return df

#handling nulls
def check_nulls(df: pd.DataFrame):
    null = df.isnull().sum()
    ratio = (null / df.shape[0])*100
    return pd.DataFrame({"null ":null, "ratio ": ratio}).T

#check outliers
def check_outliers(df:pd.DataFrame):
    num_cols = df.select_dtypes("number").columns
    for col in num_cols:
        Q1 = df[col].quantile(.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1

        lower_fence = Q1 - 1.5*IQR
        upper_fence = Q3 + 1.5*IQR

        print(f"\nColumn: {col}")
        print(f"Q1={Q1}, Q3={Q3}, IQR={IQR}")
        print(f"Lower fence={lower_fence}, Upper fence={upper_fence}")

        lower_outliers = df[df[col] < lower_fence][col].values
        print(f"{col} lower outliers:\n {lower_outliers}")

        upper_outliers = df[df[col] > upper_fence][col].values
        print(f"{col} upper outliers:\n {upper_outliers}")
        ##replacing outliers with upper or lower fence values
        #df[col] = df[col].replace(lower_outliers, lower_fence)
        #df[col] = df[col].replace(upper_outliers, upper_fence)



def removeduplicate(df, subset_cols=None, keep_stratgy = "first"):

    return (df.drop_duplicates(subset=subset_cols, keep=keep_stratgy).reset_index(drop = True))

#data visualization
def plot_categories(df, cat_cols):
    plt.figure(figsize=(14,4))
    for i , col in enumerate(cat_cols):
        plt.subplot(2,3, i+1)
        sns.countplot(x = col, data = df)
        plt.title(f"{col} count plot")

    plt.subplots_adjust(hspace =0.8, wspace=0.3)
    plt.show()

def plot_piechart(df, cat_cols):
    plt.figure(figsize=(14,4))
    for i , col in enumerate(cat_cols):
        plt.subplot(2,3, i+1)
        unique = df[col].value_counts()
        count = unique.values
        categories = unique.index
        plt.pie(count, labels = categories, autopct='%1.1f%%')
        plt.title(f"{col} pie plot")

    plt.subplots_adjust(hspace =0.8, wspace=0.3)
    plt.show()

def make_pairplot(df):
    sns.pairplot(df)
    plt.show()

def make_heatmap(df, num_cols):
    corr = df[num_cols].corr()
    plt.Figure(figsize=(2,2))
    sns.heatmap(corr, annot=True)
    plt.show()