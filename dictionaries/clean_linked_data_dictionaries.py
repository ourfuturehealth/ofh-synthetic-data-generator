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
    "apc"    : "nhse_eng_inpat",
    "op" : "nhse_eng_outpat",
    "ae" : "nhse_eng_ed",
}
OUT_PATH = "dictionaries/processed/linked-data/"

# loading the raw data dictionary and coding file from the raw folder
raw_dictionary = pd.read_excel("dictionaries/raw/our_future_health_data_dictionary_v14.xlsx", sheet_name="linked_nhse_health_records")
raw_coding_file = pd.read_excel("dictionaries/raw/our_future_health_codings_v14.xlsx", sheet_name="linked_nhse_health_records")

# splitting the dictionaries by dataset and selecting relevant columns for defining schema
df_dicts = {
    key : raw_dictionary.loc[raw_dictionary["entity"] == value, ["name", "type", "coding_name", "is_sparse_coding", "description"]] 
    for key, value in DF_NAMES.items()
}

# splitting raw coding file by dataset
df_codings = {
    key : raw_coding_file.loc[raw_coding_file["coding_name"].str.contains(key), ["coding_name", "code", "meaning"]] for key in DF_NAMES.keys()
}

# separating out ICD-10 and OPCS-4 codes from raw coding file
# using startswith for Beta version to exclude PatientTumour ICD10 coding, which is more idiosyncratic
ontology_codings = {key : raw_coding_file.loc[raw_coding_file["coding_name"].str.startswith(key.upper()), ["code", "meaning"]] for key in ["icd10", "opcs4"]}

# outputting clean dictonaries
for key, value in df_dicts.items():
    value.to_csv(OUT_PATH+"linked_data_dictionaries/"+key+"_dictionary.csv", index=False)

# outputting clean coding files
for key, value in df_codings.items():
    if len(value) > 0:
        value.to_csv(OUT_PATH+"linked_data_codings/"+key+"_codes.csv", index=False)

for key, value in ontology_codings.items():
    value.to_csv(OUT_PATH+"linked_data_codings/"+key+"_codes.csv", index=False)