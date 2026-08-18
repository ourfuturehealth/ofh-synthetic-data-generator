"""
    Script cleaning and processing the raw dictionary and coding files. 
    Creates dictionaries and coding files for Admitted Patient Care (APC), Outpatient, and ONS Death Registration Records.
    Cleaning coding files ICD-10 and OPCS-4 codes are also created.

    Cleaned dictionaries and coding files are output to processed/linked-data
"""

import pandas as pd

# defining constants
# mapping colloquial names to entity names on TRE for legibility
DF_NAMES = {
    "deaths" : "nhse_engwal_deaths",
    "apc"    : "nhse_engwal_inpat",
    "op" : "nhse_engwal_outpat"
}
OUT_PATH = "dictionaries/processed/linked-data/"

# loading the raw data dictionary and coding file from the raw folder
raw_dictionary = pd.read_excel("../raw/our_future_health_data_dictionary_v14.xlsx", sheet_name="linked_nhse_health_records")
raw_coding_file = pd.read_excel("../raw/our_future_health_codings_v14.xlsx", sheet_name="linked_nhse_health_records")

# splitting the dictionaries by dataset and selecting relevant columns for defining schema
df_dicts = {
    key : raw_dictionary.loc[value["entity"] == value, ["name", "type", "coding_name", "is_sparse_coding", "description"]] 
    for key, value in DF_NAMES.items()
}

# splitting raw coding file by dataset
df_codings = {
    key : raw_coding_file.loc[raw_coding_file["coding_name"].str.contains(key), ["coding_name", "code", "meaning"]] for key in DF_NAMES.keys()
}
# cleaning column name for legibility and easier merging
for key, value in df_codings.items():
    # some datasets do not have set codes which appear in the coding file
    if len(value) > 0:
        value["name"] = value["coding_name"].replace("", f"_{key}_coding")

# separating out ICD-10 and OPCS-4 codes from raw coding file
ontology_codings = {key : raw_coding_file.loc[raw_coding_file["coding_name"].str.contains(key.upper()), "code", "meaning"] for key in ["icd10", "opcs4"]}

# outputting clean dictonaries
for key, value in df_dicts.items():
    value.to_csv(OUT_PATH+"ld_dictionaries/"+key+"_dictionary.csv", index=False)

# outputting clean coding files
for key, value in df_codings.items():
    if len(value) > 0:
        value.to_csv(OUT_PATH+"ld_codings/"+key+"_codes.csv", index=False)

for key, value in ontology_codings.items():
    value.to_csv(OUT_PATH+"ld_codings/"+key+"codes.csv", index=False)