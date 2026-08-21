import pandas as pd
import random
import string
# import datetime
import re
import numpy as np

# from typing import Any
from pathlib import Path
from faker import Faker
# from faker.providers import DynamicProvider, BaseProvider
from ofh_synthetic_data.constants import DATE_BOOKENDS, ONTOLOGY_DICT

def load_linked_dictionary(path: Path, df_name:str) -> pd.DataFrame:
    """
    Reading linked data dictionary.
    Returns: Pandas dataframe with dictionary of field names, data types and descriptions
    """
    return pd.read_csv(path+df_name+"_dictionary.csv")

def load_linked_codes(path: Path, df_name: str) -> pd.DataFrame:
    """
    Reading code fields. 
    Returns: Pandas dataframe with codes and meanings.
    """
    return pd.read_csv(path+df_name+"_codes.csv")

def get_dictionaries(path: Path, df_name:str, ontology_dict:dict[str, str]=ONTOLOGY_DICT) -> dict[str, pd.DataFrame]:
    """
    Extracting data dictionary and any relevant codings files for a given dataset. 
    Returns: dictionary containing field dictionary, codings file, and ontologies fields, where relevant
    """
    # creating empty dictionary to populate with dictionary and coding information
    df_dict = {}
    # loading the data dictionary. All datasets must have this.
    df_dict["dictionary"] = load_linked_dictionary(path=path+"linked_data_dictionaries/", df_name=df_name)

    # extracting the coded column names to determine if coding file is present 
    coding_names = [x for x in df_dict["dictionary"]["coding_name"].unique() if x is not np.nan]
    # separating out the onology coding names
    ontologies_present = [x for x in coding_names if re.search("|".join([k.upper() for k in ONTOLOGY_DICT.keys()]), x)]

    # determine which ontology files to load, this could be multiple per dictionary
    if len(ontologies_present) > 0:
        for ontology in ontologies_present:
                df_dict[ontology] = load_linked_codes(path=path+"linked_data_codings/", df_name=ontology.replace("_coding", "").lower())  

    # load dataset-specific coding files
    if len([x for x in coding_names if x not in ontologies_present]) > 0:
        df_dict["codes"] = load_linked_codes(path=path+"linked_data_codings/", df_name=df_name)

    return df_dict

def extract_date_fields(data_dictionary: pd.DataFrame) -> list[str]:
    """
    Extracts date fields from field list.
    Returns: list of fields with date type
    """
    return data_dictionary.loc[data_dictionary["type"] == "date", "name"].unique()

def generate_row_number(df:pd.DataFrame) -> pd.DataFrame:
    """
    Adds ROW_ID field to a given dataset.
    Returns: Pandas dataframe with additional ROW_ID column.
    """
    df['ROW_ID'] = df.reset_index().index
    return df

# def pick_random_code(df_name: str, data_dictionary: dict[str, pd.DataFrame], seed:int):
#     fake = Faker()
#     Faker.seed(seed)
#     return fake.random_element(elements=data_dictionary[df_name]["code"].unique())

def create_coded_pairs(data_dictionary: dict[str, pd.DataFrame]) -> dict:
    """
    Creating coded pairs from the data dictionary to explicitly assign values
    """
    # creating dictionary of coded pairs to extract relevant codes
    coded_pairs = data_dictionary["dictionary"].loc[~data_dictionary["dictionary"]["coding_name"].isna(), ["name", "coding_name"]]
    # converting to dictionary of name and coding name value pairs
    return dict(
        zip(
            coded_pairs["name"], 
            coded_pairs["coding_name"]
        )
    )

def pick_random_code(fake: Faker, df_name: str, data_dictionary: dict[str, pd.DataFrame]):

    if re.search("ICD|OPCS|SNOMED", df_name):
        return fake.random_element(elements=data_dictionary[df_name]["code"].unique())
    else:
        return fake.random_element(elements=data_dictionary["codes"].loc[data_dictionary["codes"]["coding_name"] == df_name, "code"].unique())

def order_numbered_columns(coded_pairs_dict: dict) -> dict[str, list]:
    """
    Sorts coded fields into numeric order, specifically for columns like DIAG_nn, PROC_nn, COD_CODE_nn
    Returns: dictionary with base column name as key (eg DIAG or DIAG_4) and list of all fields which fall into that category.
    """

    # getting list of all fields that are ordered
    list_columns = [x for x in coded_pairs_dict.keys() if re.search('_[0-9]+$', x)]

    # converting list into a pandas dataframe
    list_df = pd.DataFrame(list_columns, columns=["name"])

    # extracting base column name as new field
    list_df["base_colname"] = list_df["name"].str.replace("_[0-9]+$", "", regex=True)
    # creating new integer field to order the columns by
    list_df["order_col"] = pd.to_numeric(list_df["name"].apply(lambda x: x.split("_")[-1]))
    # sorting the df according to order
    list_df = list_df.sort_values(["base_colname", "order_col"])

    # returning dictionary of coded columns in correct numerical order
    return {k : list_df.loc[list_df["base_colname"] == k, "name"].to_list() for k in list_df["base_colname"].unique()}

def generate_numeric_id(n: int) -> str:
    return ''.join(random.choices(string.digits, k=n))