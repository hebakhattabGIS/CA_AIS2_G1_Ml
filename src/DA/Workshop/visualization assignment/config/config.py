'''
edit this configuration file with the details of the dataset
including filepath to the dataset
columns that needs to be droped, converted to categories,..etc
'''
#filepath to the dataset
fpath = r"C:\Users\newle\OneDrive\Desktop\CAI-S2-G1-AI\src\DA\Workshop\visualization assignment\Data\raw\insurance.csv"

#unnecessary columns/features that will be dropped 
#DROP_COLS = ["", "", ""]

#columns that will be converted to category datatype
CAT_COLS = ["sex","smoker","region"]

#numerical columns
#NUM_COLS = ["", ""]

#subset columns define subset columns to be used in removeduplicate 
# function, it defines which columns to look at when deciding 
# whether a row is a duplicate.when it is none a raw is a 
# duplicate if every column match
subset_cols = ["",""]