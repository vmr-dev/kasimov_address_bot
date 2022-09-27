# Basic parsing algorithm
# 1. Find a table of houses' addresses (dom.mingkh.ru/area/city/houses)
# 2. Get all the houses urls from the table
# 3. Traverse the url list and collect houses/companies info (scraping)
#    * Also put companies data to known_companies list variable to cache them

import re                           # Clean results
import time                         # Delay between requests

import requests                     # Get html to parse
from bs4 import BeautifulSoup       # Parsing

from dadata_address_suggester import unify_address


REQUEST_DELAY_TIME_SEC = 0.1

CITY = "kasimov"
AREA = "ryazanskaya-oblast"
TARGET_SITE_DOMAIN = "https://dom.mingkh.ru"
TARGET_HOUSES_TABLE_URL = f"{TARGET_SITE_DOMAIN}/{AREA}/{CITY}/houses"

# For caching purposes
known_companies = []


def decrypt_cloudflare_email(enc_key):
    email = ""
    k = int(enc_key[:2], 16)
    for i in range(2, len(enc_key)-1, 2):
        email += chr(int(enc_key[i:i+2], 16) ^ k)
    return email


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
            if value.text == "[email protected]":
                encrypted_email = value.find("a")
                decrypted_email = decrypt_cloudflare_email(encrypted_email)
                company_result[header.text] = decrypted_email.strip()
            else:
                company_result[header.text] = value.text.strip()
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
