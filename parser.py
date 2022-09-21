################################################################
#                      About this module                       #
################################################################
# This file contains functions for:
# 1. Parsing data from https://dom.mingkh.ru/ (houses and companies info)
# 2. Interacting with dadata API
# 3. Interacting with YDB
#
# Essentials:
# To use functions below you need:
# 1. Set up YDB and service account with YDB.[editor/viewer] rights
# 2. Create specific tables in the YDB
# 2. Set up Yandex function
#
# Basic parsing algorithm
# 1. Find a table of houses' addresses (dom.mingkh.ru/area/city/houses)
# 2. Get all the houses urls from the table
# 3. Traverse the url list and collect houses/companies info (scraping)
#    * Also put companies data to known_companies list variable to cache them

# TODO:
# 1. Change additional_info value type in the YDB from String to JSON
#
# 2. Rearrange functions to separated .py modules (there is a code chaos already):
#   - for working with database (maybe wrap it in some class)
#   - for data parsing
#   - for telegram-bot command handlers (update and query)
#   - for working with dadata api and address unification
#
# 3. Add a class wrapper for database module (so we don't have to think
#    about YDB driver initialization and other stuff)
#
# 4. Add a message queue integration for tasks
#   (after telegram request-response test)


import re                           # Clean results
import os                           # Environment vars
import time                         # Delay between requests

import ydb                          # Remote Yandex DB
import dadata                       # Unifying addresses with geocoder
import requests                     # Get html to parse
from bs4 import BeautifulSoup       # Parsing


REQUEST_DELAY_TIME_SEC = 0.1

YDB_ENDPOINT = os.getenv("YDB_ENDPOINT")
YDB_PATH = os.getenv("YDB_PATH")

DADATA_API_KEY = os.getenv("DADATA_API_KEY")
DADATA_SECRET_KEY = os.getenv("DADATA_SECRET_KEY")
dadata_api = dadata.Dadata(DADATA_API_KEY, DADATA_SECRET_KEY)

CITY = "kasimov"
AREA = "ryazanskaya-oblast"
TARGET_SITE_DOMAIN = "https://dom.mingkh.ru"
TARGET_HOUSES_TABLE_URL = f"{TARGET_SITE_DOMAIN}/{AREA}/{CITY}/houses"

# For caching purposes
known_companies = []


def make_ydb_connection() -> ydb.BaseSession:
    driver = ydb.Driver(endpoint=YDB_ENDPOINT, database=YDB_PATH)
    driver.wait(fail_fast=True, timeout=5)
    session = driver.table_client.session().create()
    return session


def request_ydb_query(session: ydb.BaseSession, yql_query: str) -> list[dict]:
    settings = \
        ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)

    result = session.transaction().execute(
        yql_query,
        commit_tx=True,
        settings=settings
    )
    return result[0].rows


def decrypt_cloudflare_email(enc_key):
    email = ""
    k = int(enc_key[:2], 16)
    for i in range(2, len(enc_key)-1, 2):
        email += chr(int(enc_key[i:i+2], 16) ^ k)
    return email


def unify_address(address: str) -> str:
    unified = dadata_api.suggest("address", address)
    if not unified:
        unified = dadata_api.clean("address", address)
        assert unified
        return unified['result']
    else:
        assert unified
        return unified[0]['value']


def get_delayed(url):
    time.sleep(REQUEST_DELAY_TIME_SEC)
    return requests.get(url).text


# Runs through the table and collects URLs of houses
def get_addresses_urls(table_entry) -> list:
    table_rows = table_entry.findAll("tr")
    address_info_urls = []
    for row in table_rows:
        a_tags = row.findAll('a', href=True)
        address_info_urls.append(TARGET_SITE_DOMAIN + a_tags[0]["href"])
    return address_info_urls


# Collects all urls of houses from the entire table
def get_houses_urls_for_city(houses_table_url: str):
    page = 1
    houses_urls = []
    while True:
        current_page_url = houses_table_url + f"?page={page}"
        current_page_html = get_delayed(current_page_url)

        current_bs = BeautifulSoup(current_page_html, features="html.parser")
        current_table = current_bs.find("tbody")

        if len(current_table.findAll("tr")) == 0:
            break

        houses_urls += get_addresses_urls(current_table)
        page += 1

    return houses_urls


def get_company_info(company_url: str):
    for company in known_companies:
        if company['url'] == company_url:
            return company

    company_page_html = get_delayed(company_url)
    company_bs = BeautifulSoup(company_page_html, features="html.parser")

    info = company_bs.find(
        "dl", attrs={"class": "dl-horizontal company margin-top-20"}
    )

    company_result = {}
    next_header = info.find('dt')
    while next_header:
        header = next_header
        value = header.findNext('dd')
        next_header = value.findNext('dt')

        if header.text.strip() == '' or value.text.strip() == '':
            continue

        if header.text.strip() == "E-mail":
            encrypted_email = value.find("a")["data-cfemail"]
            decrypted_email = decrypt_cloudflare_email(encrypted_email)
            value = decrypted_email.strip()
            company_result[header.text] = value
            continue

        value = value.text
        value = value.replace("на карте", "")
        value = value.replace("список", "")
        value = re.sub(r"\xa0(.*)", "", value)
        value = value.strip()

        company_result[header.text] = value

    company_result["url"] = company_url
    if "Адрес" in company_result.keys():
        company_result["Адрес"] = unify_address(company_result["Адрес"])

    known_companies.append(company_result)
    return company_result


def get_house_info(house_url: str):
    result_house_info = {}

    house_info_html = get_delayed(house_url)
    current_house_bs = BeautifulSoup(house_info_html, features="html.parser")

    info = current_house_bs.find("dl", attrs={"class": "dl-horizontal house"})

    next_header = info.find('dt')
    while next_header:
        header = next_header
        value = header.findNext('dd')
        next_header = value.findNext('dt')

        if header.text.strip() == '':
            continue

        # No value field or link as a value
        if header.text.find("Выписка из ЕГРН") != -1:
            continue
        if header.text.find("Капитальный ремонт") != -1:
            continue

        # Cut out trash content
        value = value.text
        value = re.sub(r"\xa0(.*)", '', value)
        value = re.sub(r"с [0-9]{2}.[0-9]{2}.[0-9]{4}(.*)", "", value)
        value = value.strip()

        result_head = header.text
        result_body = value

        if "адрес" in header.text.lower():
            result_house_info[result_head] = unify_address(value)
            continue

        result_house_info[result_head] = result_body

    if url := info.find('dt', string="Управляющая компания"):
        url = url.findNext("span")["data-url"]
        result_house_info["_meta_company_info"] = get_company_info(url)

    return result_house_info


def write_db_house(ydb_session, house_info: dict):
    houses_table_address = house_info["Адрес"]
    houses_table_additional_info = ""
    houses_table_company_name = "null"

    for key in house_info.keys():
        if ("meta" in key) or ("адрес" in key.lower()):
            continue
        houses_table_additional_info += key + ": " + house_info[key] + '\n'

    if "_meta_company_info" in house_info.keys():
        houses_table_company_name = house_info["_meta_company_info"]["Наименование"]
        houses_table_company_name = '"' + houses_table_company_name + '"'

    request_ydb_query(ydb_session, f"""
        REPLACE INTO houses (address, additional_info, company_name) VALUES
            ("{houses_table_address}", 
             "{houses_table_additional_info}", 
              {houses_table_company_name});
    """)


def write_db_company(ydb_session, company_info: dict):
    companies_table_company_name = company_info["Наименование"]
    companies_table_additional_info = ""

    for key in company_info.keys():
        if 'url' in key:
            continue

        companies_table_additional_info += key + ": " + company_info[key] + '\n'

    request_ydb_query(ydb_session, f"""
        REPLACE INTO companies (name, additional_info) VALUES
            ("{companies_table_company_name}", 
             "{companies_table_additional_info}");
    """)


def update_database(ydb_session, houses_urls: list):
    house_id = 1

    for house_url in houses_urls:
        current_house_info = get_house_info(house_url)
        write_db_house(ydb_session, current_house_info)

        if "_meta_company_info" in current_house_info.keys():
            company_info = current_house_info["_meta_company_info"]
            write_db_company(ydb_session, company_info)

        house_id += 1


# find table entry by its key value
# if there is no appropriate value - return empty list
def search_in_database(ydb_session, table: str, search_value: str) -> list[dict]:
    if table == "companies":
        key_name = "name"
    elif table == "houses":
        key_name = "address"
    else:
        return []

    query = f"""
        SELECT * FROM
        {table}
        WHERE
        {key_name} = "{search_value}"
    """
    return request_ydb_query(ydb_session, query)


# Main yandex function handler (this is an entry point for webhook)
# we need to pass some command with event
# and parse it with telegram-message-handler module
def handler(event, context):
    ydb_session = make_ydb_connection()
    # YDB Query test for connection check
    # res = requests_ydb_query(ydb_session, """
    #     SELECT * FROM companies
    # """)
    # print(res)

    return {
        'statusCode': 200,
        'body': 'Hello World!',
    }

