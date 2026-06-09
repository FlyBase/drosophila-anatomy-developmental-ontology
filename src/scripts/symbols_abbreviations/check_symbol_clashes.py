#!/usr/bin/env python3
"""Check for neuron symbols and BrainName abbreviation clashes.

Errors raised if any of these found:

  * the first file (sys.argv[1]) contains a duplicate FBbt_id or a duplicate
    symbol/abbreviation
  * the first file is missing an FBbt id or symbol/abbreviation
  * a symbol in the first file is identical to an abbreviation in the second
    file, which would be an ambiguous clash between a neuron symbol and a
    brain-region abbreviation

Usage:
    python3 check_symbol_clashes.py <file1> <file2>
"""
import sys
import re
import pandas as pd

FBBT_ID_RE = re.compile(r"^FBbt:\d{8}$")

def load(path):
    """Read a TSV as DataFrame of strings, with surrounding whitespace stripped from cells."""
    return pd.read_csv(path, sep="\t", dtype=str)\
        .fillna("")\
        .apply(lambda column: column.str.strip())

def main(file1, file2):
    df1 = load(file1)
    df1 = df1.rename(columns={"symbol":"value", "abbreviation":"value"}, errors='ignore')
    df2 = load(file2)
    df2 = df2.rename(columns={"symbol":"value", "abbreviation":"value"}, errors='ignore')
    errors = []

    # Each entry in the first file must be unique
    for column in ("FBbt_id", "value"):
        counts = df1[column].value_counts()
        duplicates = list(counts[counts > 1].index)
        if duplicates:
            errors.append(f"duplicate {column}(s) in {file1}: {duplicates}")

    # Check for missing id/value
    missing_id = df1[(df1["FBbt_id"] == "")]
    for _, row in missing_id.iterrows():
        errors.append(f"clash: '{row['value']}' has no FBbt_id in {file1}")
    
    missing_value = df1[(df1["value"] == "")]
    for _, row in missing_value.iterrows():
        errors.append(f"clash: '{row['FBbt_id']}' in {file1} has no symbol/abbreviation")
    
    bad_ids = df1[~df1["FBbt_id"].str.match(FBBT_ID_RE)]
    if len(bad_ids) > 0:
        errors.append(f"malformed FBbt IDs: {bad_ids['FBbt_id'].tolist()} in {file1}")

    # Check no id or value conflicts
    id_clashes = df1[df1["FBbt_id"].isin(df2["FBbt_id"])]
    for _, row in id_clashes.iterrows():
        errors.append(f"clash: '{row['FBbt_id']}' has a neuron symbol "
                      f"and a brain-name abbreviation")
    
    value_clashes = df1[df1["value"].isin(df2["value"])]
    for _, row in value_clashes.iterrows():
        errors.append(f"clash: '{row['value']}' is a neuron symbol "
                      f"and a brain-name abbreviation")

    if errors:
        print("ERROR: symbol/abbreviation validation failed:\n  "
              + "\n  ".join(errors), file=sys.stderr)
        sys.exit(1)

    print(f"OK: {len(df1)} rows with no duplicates and no clashes ")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
