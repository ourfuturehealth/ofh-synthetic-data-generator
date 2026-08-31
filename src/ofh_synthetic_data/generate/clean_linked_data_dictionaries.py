"""
    Script cleaning and processing the raw dictionary and coding files. 
    Creates dictionaries and coding files for all linked datasets.
    Cleaning coding files for ontologies (ICD-10, ICD-9, OPCS-4, SNOMED) also generated.

    Cleaned dictionaries and coding files are output to processed/linked-data
"""

import pandas as pd
import os
import re

from ofh_synthetic_data.generate.linked_data_transformations import check_n_files

# defining constants
OUT_PATH = "dictionaries/processed/linked-data/"

# getting raw files in directory 
raw_files = os.listdir("dictionaries/raw/")

# extracting dictionary and coding file names from the raw folder 
dictionary_file_names = {}
for d in ["data_dictionary", "codings"]:
    dictionary_file_names[d] = check_n_files(
        [x for x in raw_files if re.search(f"{d}_v[0-9]+", x)]
    )

# loading the raw data dictionary and coding file from the raw folder
raw_dictionary = pd.read_excel("dictionaries/raw/"+dictionary_file_names["data_dictionary"], sheet_name="linked_nhse_health_records")
raw_coding_file = pd.read_excel("dictionaries/raw/"+dictionary_file_names["codings"], sheet_name="linked_nhse_health_records")

# splitting the dictionaries by dataset and selecting relevant columns for defining schema
DF_NAMES = raw_dictionary["entity"].unique()

df_dicts = {
    key : raw_dictionary.loc[raw_dictionary["entity"] == key, ["name", "type", "coding_name", "is_sparse_coding", "description"]] 
    for key in DF_NAMES
}

# getting coding names for each dataset, excluding ontologies
code_mapping = {
    df_name : 
    raw_dictionary.loc[
        (raw_dictionary["entity"] == df_name) & 
        ~(raw_dictionary["coding_name"].str.contains("ICD|SNOMED|OPCS")) &
        ~(raw_dictionary["coding_name"].isna()), 
        "coding_name"].unique() 
    for df_name in DF_NAMES
}

# separating coding file by entity
coding_dict = {
    df_name : raw_coding_file.loc[raw_coding_file["coding_name"].isin(col_list), ["coding_name", "code", "meaning"]] 
    for df_name, col_list in code_mapping.items()
    if len(col_list) > 0
}

# separating out ontology codes from raw coding file
ontology_names = raw_dictionary.loc[raw_dictionary["coding_name"].str.contains("ICD|SNOMED|OPCS"), "coding_name"].unique()
ontology_codings = {
    ontology_name : raw_coding_file.loc[raw_coding_file["coding_name"] == ontology_name, ["coding_name", "code", "meaning"]] 
    for ontology_name in ontology_names
}

# outputting clean dictonaries
for key, value in df_dicts.items():
    value.to_csv(OUT_PATH+"linked_data_dictionaries/"+key+"_dictionary.csv", index=False)

# outputting clean coding files
for key, value in coding_dict.items():
    value.to_csv(OUT_PATH+"linked_data_codings/"+key+"_codes.csv", index=False)

for key, value in ontology_codings.items():
    value.to_csv(OUT_PATH+"linked_data_codings/"+key+".csv", index=False)