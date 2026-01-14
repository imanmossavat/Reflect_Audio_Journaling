RELEVANT_LABELS = {
    "PERSON",
    "ORG",
    "GPE",
    "DATE",
    "EMAIL",
    "ZIPCODE"
}

DEFAULT_PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "PHONENUMBER": r"\b(?:\+?\d{1,3})?[-.\s(]?\d{2,4}[-.\s)]?\d{2,4}[-.\s]?\d{2,4}\b",
    "ZIPCODE": r"\b[0-9]{4}\s?[A-Z]{2}\b"
}


LABEL_MAP = {
    "FIRSTNAME": "PERSON",
    "MIDDLENAME": "PERSON",
    "LASTNAME": "PERSON",
    "FULLNAME": "PERSON",
    "NAME": "PERSON",
    "USERNAME": "PERSON",
    "ACCOUNTNAME": "PERSON",

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