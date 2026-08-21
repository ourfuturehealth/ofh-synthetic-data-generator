import datetime

# dictionary defining start and end dates for the datasets
DATE_BOOKENDS = {
    "deaths" : {"start" : datetime.date(2022,6,1), "end" : datetime.date(2025,11,30)},
    "apc": {"start" : datetime.date(1997,4,1), "end" : datetime.date(2025,10,31)},
    "op": {"start" : datetime.date(2003,4,1), "end" : datetime.date(2025,10,31)},
    "ae": {"start" : datetime.date(2007,4,1), "end" : datetime.date(2019,3,31)},
}

ONTOLOGY_DICT = {
    'icd10' : ['apc', 'op', 'mort', 'histcanreg'],
    'icd9' : ['histcanreg'],
    'opcs4': ['apc', 'op'],
    'snomed': ['ecds', 'meds', 'drugs']
}

IMD_VALID_ENTRIES = [
    "Most deprived 10%", 
    "More deprived 10-20%", 
    "More deprived 20-30%", 
    "More deprived 30-40%", 
    "More deprived 40-50%", 
    "Less deprived 40-50%", 
    "Less deprived 30-40%", 
    "Less deprived 20-30%", 
    "Less deprived 10-20%", 
    "Least deprived 10%",
    "Less deprived 10%",
]