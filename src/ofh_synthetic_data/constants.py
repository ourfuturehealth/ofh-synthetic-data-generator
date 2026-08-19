# File names
ICD_CODING_FILE = "icd10_codes.csv"
OPCS_CODING_FILE = "opcs4_codes.csv"

EXTERNAL_CODE_MAP = {
    "ICD10_coding": ICD_CODING_FILE,
    "OPCS4_coding": OPCS_CODING_FILE,
}

# dictionary defining start and end dates for the datasets
DATE_BOOKENDS = {
    "deaths" : {"start" : datetime.date(2022,6,1), "end" : datetime.date(2025,11,30)},
    "apc": {"start" : datetime.date(1997,4,1), "end" : datetime.date(2025,10,31)},
    "op": {"start" : datetime.date(2003,4,1), "end" : datetime.date(2025,10,31)}
}

ONTOLOGY_DICT = {
    'icd10' : ['apc', 'op', 'mort', 'histcanreg'],
    'icd9' : ['histcanreg'],
    'opcs4': ['apc', 'op'],
    'snomed': ['ecds', 'meds', 'drugs']
}