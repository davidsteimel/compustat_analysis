import pandas as pd
import pyreadr


# Data loading:
# Load the linking file which maps Compustat's gvkey to CRSP's lpermno
link = pd.read_csv("Compustat/Compustat_Identifiers/link_file.csv")

# Load Compustat annual data
# nrows=1000 is for testing only - remove for full run
compustat_annual = pd.read_csv("Compustat/data/C_NA_annual/Compustat_NA_annual.csv",
                                sep="\t", nrows=1000, low_memory=False)

# Load Compustat quarterly data
compustat_quarterly = pd.read_csv("Compustat/data/1-Part-Compustat_NA.csv",
                                   sep="\t",nrows=1000, low_memory=False)

# Load CRSP monthly stock data from RDS format
# [None] extracts the single dataframe stored inside the RDS file
crsp = pyreadr.read_r("crspdata/caz202412_r/StkMthSecurityData.rds")[None]


# Data preprocessing for linking:
# Convert date columns to datetime with UTC timezone to avoid
# timezone-comparison errors during the merge (tz-naive vs tz-aware conflict).
link["linkdt"] = pd.to_datetime(link["linkdt"], format="mixed", errors="coerce", utc=True)
link["linkenddt"] = pd.to_datetime(link["linkenddt"], format="mixed", errors="coerce", utc=True)

# Fill missing end dates with a far-future date - an empty linkenddt means the link is still active
link["linkenddt"] = link["linkenddt"].fillna(pd.Timestamp("2099-12-31", tz="UTC"))

# Keep only primary links (linkprim = P or C) to avoid duplicate matches
link_permno = link[link["linkprim"].isin(["P", "C"])][
    ["gvkey", "lpermno", "cusip", "linkdt", "linkenddt"]
].drop_duplicates()


def add_cusip_to_compustat(compustat_df, date_col):
    df = compustat_df.copy()

    # Convert reporting date to UTC-aware datetime for timezone-safe comparison
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)

    # Merge Compustat with the linking file on gvkey
    # Left join keeps all Compustat rows, even if no link exists
    df = df.merge(
        link_permno[["gvkey", "cusip", "lpermno", "linkdt", "linkenddt"]],
        left_on="COMPANY_GVKEY",
        right_on="gvkey",
        how="left"
    )

    # Time filter: only keep rows where the Compustat reporting date falls within the valid period of the link
    df = df[
        (df[date_col] >= df["linkdt"]) &
        (df[date_col] <= df["linkenddt"])
    ]

    # Drop linking file helper columns that are no longer needed
    df = df.drop(columns=["gvkey", "linkdt", "linkenddt"])

    print(f"  -> Added CUSIP: {df['cusip'].notna().sum()} of {len(df)} rows have a CUSIP")
    return df


def merge_via_linkfile(compustat_df, date_col):
    """
    Merges a Compustat DataFrame with CRSP monthly data using lpermno as the key.

    Parameters:
        compustat_df : pd.DataFrame  - Compustat dataset with lpermno column
        date_col     : str           - Name of the date column in compustat_df

    Returns:
        pd.DataFrame - Merged dataset with all Compustat and CRSP columns
    """
    df = compustat_df.copy()

    # Select only the relevant CRSP columns to reduce memory usage
    crsp_slim = crsp[["PERMNO", "MthCalDt", "MthRet", "MthRetx",
                       "MthCap", "MthPrc", "MthVol", "Ticker", "CUSIP"]].copy()
    crsp_slim["MthCalDt"] = pd.to_datetime(crsp_slim["MthCalDt"], errors="coerce", utc=True)

    # Extract year from both datasets for year-based matching
    crsp_slim["_year"] = crsp_slim["MthCalDt"].dt.year
    df["_year"] = df[date_col].dt.year

    # Merge on lpermno (from linking file) and year
    # Left join keeps all Compustat rows even without a CRSP match
    merged = df.merge(
        crsp_slim,
        left_on=["lpermno", "_year"],
        right_on=["PERMNO", "_year"],
        how="left"
    ).drop(columns=["_year"])

    return merged

def merge_via_cusip(compustat_df, date_col):
    """
    Merges a Compustat DataFrame with CRSP monthly data directly using
    CUSIP as the identifier 

    Note: Compustat uses 9-digit CUSIPs, CRSP uses 8-digit CUSIPs.
    Both are trimmed to 8 characters before merging

    This method serves as an alternative and validation tool against the
    linking file approach. It typically has slightly lower match rates
    because CUSIPs can change over time and formatting may differ.

    Parameters:
        compustat_df : pd.DataFrame  - Compustat dataset with 'cusip' column
        date_col     : str           - Name of the date column in compustat_df

    Returns:
        pd.DataFrame - Merged dataset with all Compustat and CRSP columns
    """
    df = compustat_df.copy()

    # Select only the relevant CRSP columns to reduce memory usage
    crsp_slim = crsp[["PERMNO", "MthCalDt", "MthRet", "MthRetx",
                       "MthCap", "MthPrc", "MthVol", "Ticker", "CUSIP"]].copy()
    crsp_slim["MthCalDt"] = pd.to_datetime(crsp_slim["MthCalDt"], errors="coerce")

    # Extract year from both datasets for year-based matching
    crsp_slim["_year"] = crsp_slim["MthCalDt"].dt.year
    df["_year"] = df[date_col].dt.year

    # Standardize CUSIP to 8 characters:
    # Compustat: 9-digit CUSIP → trim to 8
    # CRSP:      8-digit CUSIP → stays the same
    df["cusip_8"] = df["cusip"].astype(str).str[:8]
    crsp_slim["cusip_8"] = crsp_slim["CUSIP"].astype(str).str[:8]

    # Merge on standardized 8-digit CUSIP and year
    merged = df.merge(
        crsp_slim,
        left_on=["cusip_8", "_year"],
        right_on=["cusip_8", "_year"],
        how="left"
    ).drop(columns=["_year", "cusip_8"])

    return merged



def check_merge_accuracy(result_linkfile, result_cusip, key_col="COMPANY_GVKEY"):
    """
    Compares the quality of the two merge approaches.

    Three metrics are reported:
    1. Match rate (linking file): % of rows that received CRSP data
    2. Match rate (CUSIP):        % of rows that received CRSP data
    3. PERMNO agreement: where both methods found a match, how often do they
       agree on the same PERMNO (i.e. the same security)?
       Note: 
       High agreement (>95%) confirms both methods identify the same company.

    Parameters:
        result_linkfile : pd.DataFrame - Output of merge_via_linkfile()
        result_cusip    : pd.DataFrame - Output of merge_via_cusip()
        key_col         : str          - Column to join on for PERMNO comparison
                                         (default: "COMPANY_GVKEY")
    """
    print("MERGE ACCURACY CHECK")

    # Count rows where MthRet is not NaN - if NaN, no CRSP match was found
    lf_matched = result_linkfile["MthRet"].notna().sum()
    lf_total   = len(result_linkfile)
    cu_matched = result_cusip["MthRet"].notna().sum()
    cu_total   = len(result_cusip)

    print(f"\nLinkfile-Merge:  {lf_matched:,} / {lf_total:,} rows matched "
          f"({100*lf_matched/lf_total:.1f}%)")
    print(f"CUSIP-Merge:     {cu_matched:,} / {cu_total:,} rows matched "
          f"({100*cu_matched/cu_total:.1f}%)")

    # Join both results on gvkey and compare PERMNOs:
    # lpermno = assigned by linking file
    # PERMNO  = returned by CRSP when matched via CUSIP
    both = result_linkfile[[key_col, "lpermno"]].merge(
        result_cusip[[key_col, "PERMNO"]],
        on=key_col,
        how="inner"
    ).dropna()

    if len(both) > 0:
        agree = (both["lpermno"].astype(str) == both["PERMNO"].astype(str)).sum()
        print(f"\nAgreement on PERMNO (where both match): "
              f"{agree:,} / {len(both):,} ({100*agree/len(both):.1f}%)")
    else:
        print("\nNo common comparison possible.")

    print("="*50 + "\n")



""" # Step 1: Add CUSIP and lpermno to Compustat annual via linking file
print("Add CUSIP to Compustat Annual")
annual_with_cusip = add_cusip_to_compustat(compustat_annual, "CO_ADESIND_DATADATE")
print(annual_with_cusip[["COMPANY_GVKEY", "COMPANY_CONM", "cusip", "lpermno"]].head(10))

# Step 2a: Merge annual Compustat with CRSP using lpermno from linking file
print(">>> Annual Merge via Linkfile...")
annual_linkfile = merge_via_linkfile(annual_with_cusip, "CO_ADESIND_DATADATE")
print(f"  -> Shape: {annual_linkfile.shape}")
print(annual_linkfile[["COMPANY_GVKEY", "COMPANY_CONM", "lpermno", "MthRet", "MthCap"]].head(10))

# Step 2b: Merge annual Compustat with CRSP directly via CUSIP
print("\n>>> Annual Merge via CUSIP...")
annual_cusip = merge_via_cusip(annual_with_cusip, "CO_ADESIND_DATADATE")
print(f"  -> Shape: {annual_cusip.shape}")
print(annual_cusip[["COMPANY_GVKEY", "COMPANY_CONM", "cusip", "MthRet", "MthCap"]].head(10))

# Step 3: Compare both merge methods
print("\n>>> Accuracy Check Annual:")
check_merge_accuracy(annual_linkfile, annual_cusip) """

# Step 1: Add CUSIP and lpermno to Compustat quarterly via linking file
print("Add CUSIP to Compustat Quarterly")
quarterly_with_cusip = add_cusip_to_compustat(compustat_quarterly, "CO_IDESIND_DATADATE")
print(quarterly_with_cusip[["COMPANY_GVKEY", "COMPANY_CONM", "cusip", "lpermno"]].head(10))

# Step 2a: Merge quarterly Compustat with CRSP using lpermno from linking file
print(">>> Quarterly Merge via Linkfile...")
quarterly_linkfile = merge_via_linkfile(quarterly_with_cusip, "CO_IDESIND_DATADATE")
print(f"  -> Shape: {quarterly_linkfile.shape}")
print(quarterly_linkfile[["COMPANY_GVKEY", "COMPANY_CONM", "lpermno", "MthRet", "MthCap"]].head(10))

# Step 2b: Merge quarterly Compustat with CRSP directly via CUSIP
print("\n>>> Quarterly Merge via CUSIP...")
quarterly_cusip = merge_via_cusip(quarterly_with_cusip, "CO_IDESIND_DATADATE")
print(f"  -> Shape: {quarterly_cusip.shape}")
print(quarterly_cusip[["COMPANY_GVKEY", "COMPANY_CONM", "cusip", "MthRet", "MthCap"]].head(10))

# Step 3: Compare both merge methods
print("\n>>> Accuracy Check Quarterly:")
check_merge_accuracy(quarterly_linkfile, quarterly_cusip)