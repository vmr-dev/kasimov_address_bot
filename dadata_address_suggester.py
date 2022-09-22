import os
import dadata

DADATA_API_KEY = os.getenv("DADATA_API_KEY")
DADATA_SECRET_KEY = os.getenv("DADATA_SECRET_KEY")
dadata_api = dadata.Dadata(DADATA_API_KEY, DADATA_SECRET_KEY)


def unify_address(address: str) -> str:
    unified = dadata_api.suggest("address", address)
    if not unified:
        unified = dadata_api.clean("address", address)
        assert unified
        return unified['result']
    else:
        assert unified
        return unified[0]['value']
