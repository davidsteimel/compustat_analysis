import pandas as pd


class CompanyProfil:
    """
    Represents a single company's Compustat data profile.
    Supports both annual (CO_ADESIND_FYEAR) and quarterly (CO_IDESIND_FYEARQ) data.
    """

    # Maps dataset type to its year column
    YEAR_COLS = {
        "quarterly": "CO_IDESIND_FYEARQ",
        "annual":    "CO_ADESIND_FYEAR"
    }

    def __init__(self, gvkey: str, name: str, data: pd.DataFrame):
        self.gvkey = gvkey
        self.name  = name

        # Auto-detect whether this is annual or quarterly data
        if "CO_IDESIND_FYEARQ" in data.columns:
            self.freq     = "quarterly"
            self.year_col = self.YEAR_COLS["quarterly"]
        elif "CO_ADESIND_FYEAR" in data.columns:
            self.freq     = "annual"
            self.year_col = self.YEAR_COLS["annual"]
        else:
            self.freq     = "unknown"
            self.year_col = None

        # Sort by year if possible
        if self.year_col:
            self.data = data.sort_values(by=self.year_col).copy()
            self.data.set_index(self.year_col, inplace=True)
            self.data.index.name = "Year"
        else:
            self.data = data.copy()

    def __repr__(self):
        return (f"<Company: {self.name} | gvkey: {self.gvkey} | "
                f"freq: {self.freq} | {len(self.data)} entries>")

    def search_variables(self, keyword: str) -> list:
        """
        Searches all column names for a keyword (case-insensitive).
        Useful when you don't know the exact column name.

        Example:
            company.search_variables("revenue")
            → ['CO_AFND2_REVT', 'CO_AFND2_SALE', ...]
        """
        keyword = keyword.upper()
        matches = [col for col in self.data.columns if keyword in col.upper()]
        if matches:
            print(f"  Columns matching '{keyword}':")
            for m in matches:
                print(f"    {m}")
        else:
            print(f"  No columns found matching '{keyword}'.")
        return matches

    def get(self, keys) -> pd.DataFrame | None:
        """
        Retrieves one or more variables by name.
        Accepts short names (e.g. 'NIQ') or full names (e.g. 'CO_IFNDQ_NIQ').
        If a short name matches multiple columns, a warning is shown.

        Example:
            company.get("NIQ")
            company.get(["NIQ", "SALEQ"])
        """
        if isinstance(keys, str):
            keys = [keys]

        found_columns = []
        for key in keys:
            search_key = key.upper()
            matches = []

            for col in self.data.columns:
                # Exact match
                if col.upper() == search_key:
                    matches.append(col)
                # Match on the suffix after the last underscore (e.g. NIQ from CO_IFNDQ_NIQ)
                elif col.upper().endswith("_" + search_key):
                    matches.append(col)

            if len(matches) == 1:
                print(f"  Found: {matches[0]}")
                found_columns.append(matches[0])
            elif len(matches) > 1:
                print(f"  Warning: '{key}' is ambiguous. Matches: {matches}")
                print(f"  Please use the full column name.")
                return None
            else:
                print(f"  ERROR: Variable '{key}' not found. "
                      f"Try search_variables('{key}') to find similar columns.")

        return self.data[found_columns] if found_columns else None

    def get_period(self, keys, year_from: int = None, year_to: int = None) -> pd.DataFrame | None:
        """
        Retrieves variables filtered by a year range.

        Parameters:
            keys      : str or list - variable name(s) to retrieve
            year_from : int         - start year (inclusive), None = no lower bound
            year_to   : int         - end year (inclusive),   None = no upper bound

        Example:
            company.get_period("NIQ", year_from=2010, year_to=2020)
        """
        df = self.get(keys)
        if df is None:
            return None

        if year_from is not None:
            df = df[df.index >= year_from]
        if year_to is not None:
            df = df[df.index <= year_to]

        if df.empty:
            print(f"  No data found for the period {year_from} - {year_to}.")
            return None

        return df

 
    def summary(self, keys) -> pd.DataFrame | None:
        """
        Returns basic summary statistics (mean, std, min, max, etc.)
        for the requested variables.

        Example:
            company.summary(["NIQ", "SALEQ"])
        """
        df = self.get(keys)
        if df is None:
            return None

        stats = df.describe().T  # Transpose so variables are rows
        print(f"\n  Summary statistics for {self.name}:")
        print(stats)
        return stats

    def compare(self, other: "CompanyProfil", keys) -> pd.DataFrame | None:
        """
        Compares this company's variables with another CompanyProfil
        side by side, aligned by year.

        Parameters:
            other : CompanyProfil - the company to compare against
            keys  : str or list   - variable name(s) to compare

        Example:
            apple.compare(microsoft, "NIQ")
        """
        df_self  = self.get(keys)
        df_other = other.get(keys)

        if df_self is None or df_other is None:
            return None

        # Rename columns to include company name for clarity
        df_self  = df_self.add_suffix(f"_{self.name}")
        df_other = df_other.add_suffix(f"_{other.name}")

        # Align on year index
        combined = df_self.join(df_other, how="outer")
        print(f"\n  Comparison: {self.name} vs {other.name}")
        print(combined)
        return combined