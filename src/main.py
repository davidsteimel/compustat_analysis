import pandas as pd
from data_loader import load_data
from profiling import CompanyProfil
import pyarrow as pa
import pyarrow.parquet as pq
import csv


def main():
    path_part1 = 'Compustat/data/1-Part-Compustat_NA.csv'
    df = load_data(path_part1, rows=10000, sep='\t')

    if df is None:
        return
    grouped = df.groupby('COMPANY_GVKEY')

    companies_by_id = {}
    name_dict = {}
    all_data = []

    # each grouped object looks like (gvkey, DataFrame) and in DataFrame all rows for this gvkey
    for gvkey, group_data in grouped:
        company_name = group_data['COMPANY_CONM'].iloc[0]
            
        new_company = CompanyProfil(gvkey, company_name, group_data)
        companies_by_id[gvkey] = new_company
        name_dict[company_name.upper()] = gvkey

    print(f"{len(companies_by_id)} Company profiles created.")
    #print("Examples of loaded companies:", list(name_dict.keys())[:20])

    input_companies = input("Enter company name (separated by , ): ")
    company_names = [name.strip().upper() for name in input_companies.split(',')]
    input_vars = input("Enter variable name(s) to retrieve (separated by , ): ")
    variable_names = [var.strip() for var in input_vars.split(',')]

    for company_name in company_names:
        if company_name in name_dict:
            gvkey = name_dict[company_name]
            company_profile = companies_by_id[gvkey]
            raw_data = company_profile.get(variable_names)
            if raw_data is not None:
                variable_data = raw_data.copy()
                print(f"Found data for {company_name}")
                print(variable_data.head())
                variable_data["gvkey"] = gvkey
                variable_data["Company"] = company_name
                cols = ['Company', 'gvkey'] + [c for c in variable_data.columns if c not in ['Company', 'gvkey']]
                variable_data = variable_data[cols]
                all_data.append(variable_data)
            else:
                print(f"No data found for company '{company_name}' with variables {variable_names}.")
        else:
            print(f"Company '{company_name}' not found.")
    
    input_save_file = input("Do you want to save the output to a file? (yes/no): ").strip().lower()
    if input_save_file == 'yes':
        if len(all_data) > 0:
            combined_df = pd.concat(all_data)
            output_file = input("Enter output file name and type (e.g., output.csv or output.parquet): ").strip()

            if output_file.endswith('.csv'):
                combined_df.to_csv(output_file)
                print(f"Data saved to {output_file}")

            elif output_file.endswith('.parquet'):
                combined_df.to_parquet(output_file)
                print(f"Data saved to {output_file}")
            
            else:
                print("Unsupported file format. Please use .csv or .parquet")
        else:
            print("No data to save.")

if __name__ == "__main__":
    main()