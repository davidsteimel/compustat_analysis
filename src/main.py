import pandas as pd
from data_loader import load_data
from profiling import CompanyProfil


def build_company_profiles(df: pd.DataFrame) -> tuple[dict, dict]:
    """
    Groups the Compustat DataFrame by COMPANY_GVKEY and creates
    a CompanyProfil object for each company.

    Returns:
        companies_by_id : dict - {gvkey: CompanyProfil}
        name_dict       : dict - {COMPANY_NAME_UPPER: gvkey}
    """
    grouped        = df.groupby("COMPANY_GVKEY")
    companies_by_id = {}
    name_dict       = {}

    for gvkey, group_data in grouped:
        company_name                = group_data["COMPANY_CONM"].iloc[0]
        new_company                 = CompanyProfil(gvkey, company_name, group_data)
        companies_by_id[gvkey]      = new_company
        name_dict[company_name.upper()] = gvkey

    print(f"{len(companies_by_id)} company profiles created.")
    return companies_by_id, name_dict


def find_company(query: str, name_dict: dict) -> list:
    """
    Searches for companies by partial name match (case-insensitive).
    Returns a list of matching company names.

    Example:
        find_company("apple", name_dict) → ["APPLE INC"]
    """
    query   = query.strip().upper()
    matches = [name for name in name_dict if query in name]
    return matches


def save_output(combined_df: pd.DataFrame):
    """Asks the user for a filename and saves the DataFrame to CSV or Parquet."""
    output_file = input("Enter output filename (e.g. output.csv or output.parquet): ").strip()

    if output_file.endswith(".csv"):
        combined_df.to_csv(output_file)
        print(f"  Saved to {output_file}")
    elif output_file.endswith(".parquet"):
        combined_df.to_parquet(output_file)
        print(f"  Saved to {output_file}")
    else:
        print("  Unsupported format. Please use .csv or .parquet")


def main():
    path = "Compustat/data/1-Part-Compustat_NA.csv"
    # path = "Compustat/data/C_NA_annual/Compustat_NA_annual.csv"

    df = load_data(path, rows=20000, sep="\t")
    if df is None:
        return

    companies_by_id, name_dict = build_company_profiles(df)
    print("Examples:", list(name_dict.keys())[:10])

    all_data = []

    while True:
        print("\n" + "="*50)
        print("OPTIONS:")
        print("  [1] Get variables for company/companies")
        print("  [2] Get variables for a time period")
        print("  [3] Compare two companies")
        print("  [4] Show summary statistics")
        print("  [5] Search for a company by name")
        print("  [6] Search for a variable by keyword")
        print("  [q] Quit and save data")
        print("="*50)

        choice = input("Choose an option: ").strip().lower()

        if choice == "q":
            if all_data:
                save_choice = input("\nSave collected data to file? (yes/no): ").strip().lower()
                if save_choice == "yes":
                    combined_df = pd.concat(all_data)
                    save_output(combined_df)
                else:
                    print("  Data not saved.")
            else:
                print("  No data collected, nothing to save.")
            break

        elif choice == "5":
            # Partial company name search
            query   = input("Enter partial company name: ").strip()
            matches = find_company(query, name_dict)
            if matches:
                print(f"  Found {len(matches)} match(es):")
                for m in matches[:20]:  # show max 20 results
                    print(f"    {m}")
            else:
                print("  No companies found.")

        elif choice == "6":
            # Variable keyword search - needs a company to search in
            company_input = input("Enter company name to search in: ").strip().upper()
            matches       = find_company(company_input, name_dict)

            if not matches:
                print(f"  Company '{company_input}' not found.")
                continue

            gvkey   = name_dict[matches[0]]
            company = companies_by_id[gvkey]
            keyword = input("Enter variable keyword to search for: ").strip()
            company.search_variables(keyword)

        elif choice in ["1", "2", "3", "4"]:
            # All options need at least one company and variable
            input_companies = input("Enter company name(s) (separated by , ): ")
            company_names   = [n.strip().upper() for n in input_companies.split(",")]

            input_vars     = input("Enter variable name(s) (separated by , ): ")
            variable_names = [v.strip() for v in input_vars.split(",")]

            # Optional year filter for option 2
            year_from, year_to = None, None
            if choice == "2":
                try:
                    year_from = int(input("From year (leave blank for no limit): ").strip() or 0) or None
                    year_to   = int(input("To year (leave blank for no limit): ").strip() or 0) or None
                except ValueError:
                    print("  Invalid year input, ignoring year filter.")

            # Option 3: compare exactly two companies
            if choice == "3":
                if len(company_names) != 2:
                    print("  Please enter exactly two company names separated by ','.")
                    continue
                
                name_a, name_b = company_names
                
                matches_a      = find_company(name_a, name_dict)
                matches_b      = find_company(name_b, name_dict)

                if not matches_a:
                    print(f"  Company '{name_a}' not found.")
                    continue
                if not matches_b:
                    print(f"  Company '{name_b}' not found.")
                    continue

                company_a = companies_by_id[name_dict[matches_a[0]]]
                company_b = companies_by_id[name_dict[matches_b[0]]]
                result    = company_a.compare(company_b, variable_names)

                if result is not None:
                    all_data.append(result)
                continue

            # Options 1, 2, 4: iterate over companies
            for company_name in company_names:
                matches = find_company(company_name, name_dict)

                if not matches:
                    print(f"  Company '{company_name}' not found.")
                    # Show similar names if available
                    suggestions = [n for n in name_dict if company_name[:4] in n][:5]
                    if suggestions:
                        print(f"  Did you mean: {suggestions}?")
                    continue

                # If multiple matches, use the first and inform user
                if len(matches) > 1:
                    print(f"  Multiple matches found: {matches[:5]}")
                    print(f"  Using: {matches[0]}")

                gvkey   = name_dict[matches[0]]
                company = companies_by_id[gvkey]

                # Get data based on chosen option
                if choice == "1":
                    raw_data = company.get(variable_names)
                elif choice == "2":
                    raw_data = company.get_period(variable_names, year_from, year_to)
                elif choice == "4":
                    raw_data = company.summary(variable_names)

                if raw_data is not None:
                    print(f"\n  Data for {matches[0]}:")
                    print(raw_data)

                    # Add metadata columns for export
                    export_df            = raw_data.copy()
                    export_df["gvkey"]   = gvkey
                    export_df["Company"] = matches[0]
                    cols                 = ["Company", "gvkey"] + [
                        c for c in export_df.columns if c not in ["Company", "gvkey"]
                    ]
                    all_data.append(export_df[cols])


if __name__ == "__main__":
    main()