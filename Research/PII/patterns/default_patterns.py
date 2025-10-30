DEFAULT_PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "PHONENUMBER": r"\b(?:\+?\d{1,3})?[-.\s(]?\d{2,4}[-.\s)]?\d{2,4}[-.\s]?\d{2,4}\b",
    "ZIPCODE": r"\b\d{4,5}(?:[-\s]?\d{4})?\b",
    "DATE": r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
             r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s\d{1,2},?\s\d{2,4})\b",
    "CITY": r"\b(?:Amsterdam|Rotterdam|Utrecht|Eindhoven|The Hague|New York|London)\b",
    "COMPANYNAME": r"\b[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)*(?:\sLtd|BV|Inc|Corp|LLC)?\b"
}

RELEVANT_LABELS = {
    "PERSON",
    "ORG",
    "GPE",
    "LOC",
    "DATE",
    "EMAIL",
    "PHONENUMBER",
    "ZIPCODE"
}

LABEL_MAP = {
    "FIRSTNAME": "PERSON",
    "MIDDLENAME": "PERSON",
    "LASTNAME": "PERSON",
    "FULLNAME": "PERSON",
    "NAME": "PERSON",
    # "USERNAME": "PERSON",
    # "ACCOUNTNAME": "PERSON",

    "COMPANYNAME": "ORG",
    "JOBTITLE": "ORG",
    "JOBAREA": "ORG",
    "JOBTYPE": "ORG",
    "EMPLOYER": "ORG",

    "CITY": "GPE",
    "STATE": "GPE",
    "COUNTY": "GPE",
    "COUNTRY": "GPE",
    "STREET": "LOC",
    "BUILDINGNUMBER": "LOC",
    "SECONDARYADDRESS": "LOC",
    "NEARBYGPSCOORDINATE": "LOC",
    "ORDINALDIRECTION": "LOC",
    "ZIPCODE": "ZIPCODE",

    "DATE": "DATE",
    "DOB": "DATE",
    "TIME": "DATE",

    "EMAIL": "EMAIL",
    "PHONENUMBER": "PHONENUMBER",

    "CREDITCARDISSUER": "ORG",
    "CURRENCYNAME": "ORG",
    "PASSWORD": "ORG",

    "URL": "ORG",
    "MASKEDNUMBER": "ORG",
    "PREFIX": "PERSON",
    "SEX": "PERSON",
    "GENDER": "PERSON",
    "EYECOLOR": "PERSON",
    "HEIGHT": "PERSON"
}