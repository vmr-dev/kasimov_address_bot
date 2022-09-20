from bs4 import BeautifulSoup       # Parsing
import requests                     # Get html to parse
import dadata                       # Unifying addresses with geocoder
import json                         # json export
import time                         # Delay between requests
import re                           # Clean results


REQUEST_DELAY_TIME_SEC = 0
YDB_PROCESSOR_URL = ""
DADATA_API_KEY = ""
DADATA_SECRET_KEY = ""
dadata_api = dadata.Dadata(DADATA_API_KEY, DADATA_SECRET_KEY)

city = "kasimov"
area = "ryazanskaya-oblast"
target_site_domain = "https://dom.mingkh.ru"

target_site_houses_url = f"{target_site_domain}/{area}/{city}/houses"
known_companies = []


################################################################
#                  Базовый алгоритм парсинга                   #
################################################################
# 1. Находим страницу с началом таблицы адресов домов
# 2. Вытаскиваем url-ы с информацией по каждому дому
# 3. Собираем по каждому полученному url информацию об адресах
#    - При этом сохраняем ссылку на компанию (если есть),
#
# 4. Для каждого адреса (дома) собираем информацию о его компании,
#    для этого смотрим, есть ли у нас эти данные локально, если да
#    то просто ссылаемся на них, иначе собираем инфо о компании и бросаем в
#    список новую известную компанию
#
# 5. Обновление базы данных происходит прямо во время парсинга
#    с помощью соответствующих функций


# Выполняет запрос к базе данных и возвращает ответ в виде словаря
def request_ydb_query(query):
    res = requests.get(YDB_PROCESSOR_URL, params={"query": query}).text
    return json.loads(res)


def decrypt_cloudflare_email(enc_key):
    email = ""
    k = int(enc_key[:2], 16)
    for i in range(2, len(enc_key)-1, 2):
        email += chr(int(enc_key[i:i+2], 16) ^ k)
    return email


def unify_address(address: str) -> str:
    unified = dadata_api.suggest("address", address)
    if not unified:
        print("PAID API was used")
        unified = dadata_api.clean("address", address)
        assert unified
        return unified['result']
    else:
        assert unified
        return unified[0]['value']


def get_delayed(url):
    time.sleep(REQUEST_DELAY_TIME_SEC)
    return requests.get(url).text


# Бегает по таблице и собирает url-ки домов
def get_addresses_urls(table_entry) -> list:
    table_rows = table_entry.findAll("tr")
    address_info_urls = []
    for row in table_rows:
        a_tags = row.findAll('a', href=True)
        address_info_urls.append(target_site_domain + a_tags[0]["href"])
    return address_info_urls


# Собирает все url домов со всей таблицы
def get_houses_urls_for_city(houses_table_url: str):
    page = 1
    houses_urls = []
    while True:
        print("In processing:", page, "page")
        current_page_url = houses_table_url + f"?page={page}"
        current_page_html = get_delayed(current_page_url)

        current_bs = BeautifulSoup(current_page_html, features="html.parser")
        current_table = current_bs.find("tbody")

        if len(current_table.findAll("tr")) == 0:
            print("Table is over")
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

        # Debug:
        # print('HEAD: "' + result_head + '"')
        # print('VALUE: "' + result_body + '"')

        if "адрес" in header.text.lower():
            result_house_info[result_head] = unify_address(value)
            continue

        result_house_info[result_head] = result_body

    if url := info.find('dt', string="Управляющая компания"):
        url = url.findNext("span")["data-url"]
        result_house_info["_meta_company_info"] = get_company_info(url)

    return result_house_info


def write_db_house(house_info: dict):
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

    request_ydb_query(f"""
        REPLACE INTO houses (address, additional_info, company_name) VALUES
            ("{houses_table_address}", 
             "{houses_table_additional_info}", 
              {houses_table_company_name});
    """)


def write_db_company(company_info: dict):
    companies_table_company_name = company_info["Наименование"]
    companies_table_additional_info = ""

    for key in company_info.keys():
        if 'url' in key:
            continue

        companies_table_additional_info += key + ": " + company_info[key] + '\n'

    request_ydb_query(f"""
        REPLACE INTO companies (name, additional_info) VALUES
            ("{companies_table_company_name}", 
             "{companies_table_additional_info}");
    """)



def update_database(houses_urls: list):
    house_id = 1

    for house_url in houses_urls:
        current_house_info = get_house_info(house_url)
        write_db_house(current_house_info)

        if "_meta_company_info" in current_house_info.keys():
            company_info = current_house_info["_meta_company_info"]
            write_db_company(company_info)

        print(f"House ID {house_id} was processed successfully")
        house_id += 1


# def search_in_database(query):
#     pass


urls = get_houses_urls_for_city(target_site_houses_url)
update_database(urls)
