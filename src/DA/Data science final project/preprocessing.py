import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns
import warnings
warnings.filterwarnings("ignore")
import config.config as cnf
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

#check data type & number of unique values
def Check_data_type(df: pd.DataFrame):
    dtype = df.dtypes
    n_uniq = df.nunique()
    return pd.DataFrame({"Dtype ": dtype, "N_unique ": n_uniq}).T

#check data type of each column in the dataframe
def print_column_dtypes(df: pd.DataFrame):
    """
    Loop through all columns in a DataFrame and print their data types.
    """
    for col in df.columns:
        print(f"{col}: {df[col].dtype}")

#print unique values for a column list [category columns]
def print_unique_values(df, cols):
    """
    Print unique values for each column in a given list.
    """
    for col in cols:
        if col in df.columns:
            print(f"\nUnique values in '{col}':")
            print(df[col].unique())
        else:
            print(f"\nColumn '{col}' not found in DataFrame.")

#display n rows as sample data
def show_sample(df, n=15):
    """
    Display the first n rows of a DataFrame.
    """
    print(df.head(n))

#get descriptive statitics of numeric columns
def numeric_describe(df):
    """
    Return descriptive statistics for numeric variables only.
    """
    return df.describe()

#statistics descriptive table
def numeric_stats(df):
    """
    Return a clean, organized descriptive statistics table 
    for numeric variables in the DataFrame.
    """
    # Select numeric columns only
    num_df = df.select_dtypes(include=['int64', 'float64'])

    # Basic describe table
    desc = num_df.describe().T  # transpose for readability

    # Add extra useful columns
    desc['missing'] = num_df.isnull().sum()
    desc['unique'] = num_df.nunique()
    desc['dtype'] = num_df.dtypes

    # Reorder columns for readability
    desc = desc[['dtype', 'count', 'unique', 'missing', 'mean', 'std', 'min', '25%', '50%', '75%', 'max']]

    return desc



#handle Category columns
def define_category_features(df: pd.DataFrame, cols_to_cat: list[str])->pd.DataFrame:
    columns = cols_to_cat
    df[columns] =df[columns].astype("category")
    return df

#checking for nulls
def check_nulls(df: pd.DataFrame):
    null = df.isnull().sum()
    ratio = (null / df.shape[0])*100
    return pd.DataFrame({"null ":null, "ratio ": ratio}).T

#handling missing values
def fill_missing_values(df: pd.DataFrame):
    """
    Fill missing values:
    - Numeric columns → median
    - Categorical/object columns → mode
    """
    # Fill numeric columns (any dtype that is a number)
    num_cols= []
    num_cols = df.select_dtypes('number').columns
    for col in num_cols:
        median_value = df[col].median()
        df[col]=df[col].fillna(median_value, inplace=True)

    # Fill categorical/string columns
    str_cols=[]
    str_cols= df.select_dtypes('object').columns
    for col in str_cols:
        mode_value = df[col].mode()[0]
        df[col]= df[col].fillna(mode_value, inplace=True)

    return df




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