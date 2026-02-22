import pandas as pd

df = pd.read_parquet('testoutput.parquet')
print(df)
print("\nInfo about the DataFrame:")
print(df.info())