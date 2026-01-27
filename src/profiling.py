import pandas as pd

class CompanyProfil:
    def __init__(self, gvkey: str, name: str, data: pd.DataFrame):
        self.gvkey = gvkey
        self.name = name

        if 'CO_IDESIND_FYEARQ' in data.columns:
            self.data = data.sort_values(by='CO_IDESIND_FYEARQ')
        else:
            self.data = data
        self.data.set_index('CO_IDESIND_FYEARQ', inplace=True)
        self.data.index.name = 'Year'

    def __repr__(self):
        return f"<Company: {self.name} (gvkey: {self.gvkey}) with {len(self.data)} entries>"
    

    def get(self, keys: str):
        if isinstance(keys, str):
            keys = [keys]

        found_columns = []

        for key in keys:
            search_key = key.upper()
            matches = []
            for col in self.data.columns:
                if col == search_key:
                    matches.append(col)
                elif "_" in col and col.split("_")[-1] == search_key:
                    matches.append(col)

            if len(matches) == 1:
                full_name = matches[0]
                print(f"Found column {full_name}")
                return self.data[full_name]
            
            elif len(matches) > 1:
                print(f"Warning: '{key}' is not unique. Could be: {matches}")
                return None
                
            else:
                print(f"ERROR: Variable '{key}' not found.")

        if found_columns:
            return self.data[found_columns]
        
        else:
            return None