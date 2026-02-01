import pandas as pd

# Datei laden
df = pd.read_parquet('testoutput.parquet')

# Mal schauen, was drin ist
print(df)
print("\nInfo about the DataFrame:")
print(df.info())