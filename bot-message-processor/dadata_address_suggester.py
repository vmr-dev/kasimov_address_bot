import os
import dadata

DADATA_API_KEY = os.getenv("DADATA_API_KEY")
DADATA_SECRET_KEY = os.getenv("DADATA_SECRET_KEY")
dadata_api = dadata.Dadata(DADATA_API_KEY, DADATA_SECRET_KEY)


# UNRESTRICTED version of address unifier
def unify_address(address: str, use_paid = True) -> str:
    unified = dadata_api.suggest("address", address)
    if not unified:
        if use_paid:
            unified = dadata_api.clean("address", address)
            return unified['result']
        else:
            return ""

    return unified[0]['value']
