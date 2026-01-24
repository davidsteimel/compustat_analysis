import pandas as pd
import data_loader

path_part1 = 'Compustat/data/1-Part-Compustat_NA.csv'

df = data_loader.load_data(path_part1, 50, sep='\t')
#print(df.head())

print(df[['COMPANY_CONM', 'CO_IDESIND_FYEARQ', 'CO_IFNDQ_SALEQ']].head())

print("\nAnzahl Zeilen mit echtem Umsatz:")
print(df['CO_IFNDQ_SALEQ'].notna().sum())