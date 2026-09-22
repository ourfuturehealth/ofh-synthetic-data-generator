import pandas as pd
import random
import string
import datetime
import re
import numpy as np

from typing import Iterable

# from typing import Any
from pathlib import Path
from faker import Faker
# from faker.providers import DynamicProvider, BaseProvider
from ofh_synthetic_data.constants import DATE_BOOKENDS

def check_n_files(file_list:list[str]) -> str:
  """
  Checks correct number of file names appear in list.
  Raises exception error when more than 1 file is present or no files are present.

  Returns: string with file name
  """
  # printing warning if more than one file is present in the folder
  if len(file_list) > 1:
      raise Exception("WARNING: Multiple files in folder")
  elif len(file_list) == 0:
      raise Exception("ERROR: No files found")
  else: 
      return file_list[0]

def get_dictionaries(path: Path, df_name:str) -> dict[str, pd.DataFrame]:
    """
    Extracting data dictionary and any relevant codings files for a given dataset. 
    Returns: dictionary containing field dictionary, codings file, and ontologies fields, where relevant
    """
    # creating empty dictionary to populate with dictionary and coding information
    df_dict = {}
    # loading the data dictionary. All datasets must have this.
    df_dict["dictionary"] = pd.read_csv(path+"linked_data_dictionaries/"+df_name+"_dictionary.csv")

    # extracting the coded column names to determine if coding file is present 
    coding_names = [x for x in df_dict["dictionary"]["coding_name"].unique() if not pd.isnull(x)]
    
    if len(coding_names) > 0:
        # separating out the onology coding names
        ontologies_present = [x for x in coding_names if re.search("ICD|OPCS|SNOMED", x)]

        # determine which ontology files to load, this could be multiple per dictionary
        if len(ontologies_present) > 0:
            for ontology in ontologies_present:
                    df_dict[ontology] = pd.read_csv(path+"linked_data_codings/"+ontology+".csv")  

        # load dataset-specific coding files
        if len([x for x in coding_names if x not in ontologies_present]) > 0:
            df_dict["codes"] = pd.read_csv(path+"linked_data_codings/"+df_name+"_codes.csv")

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

def get_max_years(df_name: str, date_dict: dict=DATE_BOOKENDS) -> int:
        """
        Returns the number of years available within a given dataset based on the start and end dates defined in DATE_BOOKENDS.
        """
        return len([x for x in range(date_dict[df_name]["start"].year, date_dict[df_name]["end"].year+1)])

def generate_apc_dates(fake: Faker, pid: str, date_set: Iterable[str], anchor_date_col: str) -> dict[str, object]:
    """
    Populates date fields within APC. 

    record_dict: dictionary where generated data is saved
    date_list: list of date fields to be populated
    anchor_date_col: date column that bounds the logic for other date columns. For example, EPISTART in APC.
    """

    # generating dictionary
    record_dict = {}
    record_dict["PID"] = pid

    # defining columns that are not available for all years of data
    CONDITIONAL_DATE_FIELDS = {"DISREADYDATE", "RTTPERSTART", "RTTPEREND"}
    # defining start date for conditional date fields as 07/08 financial year
    FYEAR_START_DATE_0708 = datetime(2007, 4, 1)

    # setting anchor date
    record_dict[anchor_date_col] = fake.date_between(start_date=DATE_BOOKENDS["nhse_eng_inpat"], end_date=DATE_BOOKENDS["nhse_eng_inpat"]-7)

    # 95% chance that EPIEND is the same as anchor date column
    if fake.pybool(5):
        record_dict["EPIEND"] = fake.date_between(start_date=record_dict[anchor_date_col], end_date=record_dict[anchor_date_col]+7)

        for d in date_set - CONDITIONAL_DATE_FIELDS:
            record_dict[d] = fake.date_between(start_date=record_dict[anchor_date_col], end_date=record_dict["EPIEND"])

        # conditionally filling date fields because not available until 07/08 financial years
        if record_dict[anchor_date_col] >= FYEAR_START_DATE_0708:
            record_dict["RTTPERSTART"] = fake.date_between(start_date=record_dict[anchor_date_col], end_date=record_dict["EPIEND"])
            record_dict["RTTPEREND"] = fake.date_between(start_date=record_dict["RTTPERSTART"], end_date=record_dict["EPIEND"])
            record_dict["DISREADYDATE"] = fake.date_between(start_date=record_dict[anchor_date_col], end_date=record_dict["EPIEND"])
        else:
            record_dict.update({d: np.nan for d in CONDITIONAL_DATE_FIELDS})
    else:
        # if anchor start date is the same as end date, then all date fields equal to anchor start date
        for d in date_set:
            if d not in CONDITIONAL_DATE_FIELDS:
                record_dict[d] = record_dict[anchor_date_col]
            # conditional date fields are only populated from 07/08 financial year
            elif record_dict[anchor_date_col] >= FYEAR_START_DATE_0708:
                record_dict[d] = record_dict[anchor_date_col]
            else: 
                record_dict[d] = np.nan

    return record_dict