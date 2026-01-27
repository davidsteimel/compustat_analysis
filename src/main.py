import pandas as pd
from data_loader import load_data
from profiling import CompanyProfil

def main():
    path_part1 = 'Compustat/data/1-Part-Compustat_NA.csv'
    df = load_data(path_part1, rows=5000, sep='\t')

    if df is None:
        return
    grouped = df.groupby('COMPANY_GVKEY')

    companies_by_id = {}
    name_dict = {}

    # each grouped object looks like (gvkey, DataFrame) and in DataFrame all rows for this gvkey
    for gvkey, group_data in grouped:
        company_name = group_data['COMPANY_CONM'].iloc[0]
            
        new_company = CompanyProfil(gvkey, company_name, group_data)
        companies_by_id[gvkey] = new_company
        name_dict[company_name.upper()] = gvkey

    print(f"{len(companies_by_id)} Company profiles created.")

    input_companies = input("Enter company name (separated by , ): ")
    company_names = [name.strip().upper() for name in input_companies.split(',')]
    input_vars = input("Enter variable name(s) to retrieve (separated by , ): ")
    variable_names = [var.strip() for var in input_vars.split(',')]

    for company_name in company_names:
        if company_name in name_dict:
            gvkey = name_dict[company_name]
            company_profile = companies_by_id[gvkey]
            variable_data = company_profile.get(variable_names)
            if variable_data is not None:
                print(variable_data)
            else:
                print(f"No data found for company '{company_name}' with variables {variable_names}.")
        else:
            print(f"Company '{company_name}' not found.")

if __name__ == "__main__":
    main()