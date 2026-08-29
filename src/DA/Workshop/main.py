from config import DROP_COLS
from preprocessing import drop_cols
import pandas as pd
df = pd.read_csv('Titanic.csv')
drop_cols(df, DROP_COLS)
