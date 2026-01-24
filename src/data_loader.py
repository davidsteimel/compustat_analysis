import pandas as pd

def load_data(file_path: str, rows: int, sep: str = ',') -> pd.DataFrame:
    try:
        df = pd.read_csv(file_path, nrows=rows, sep=sep)
        print("Data successfully loaded.")
        return df
    except FileNotFoundError:
        print(f"Error: The file at '{file_path}' was not found.")
        return None