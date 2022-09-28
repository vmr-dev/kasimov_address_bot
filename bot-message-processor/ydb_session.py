# This class encapsulate all the DB logic
# connection with YDB is establishing automatically
# with ENDPOINTS from os.getenv()
#
# it has 2 public methods
#   1. For searching in tables of DB
#   2. For updating the whole DB with parser module

import os
import ydb
import json

from parser import *

YDB_ENDPOINT = os.getenv("YDB_ENDPOINT")
YDB_PATH = os.getenv("YDB_PATH")
if (not YDB_PATH) or (not YDB_ENDPOINT):
    raise "YDB_PATH and YDB_ENDPOINT environment variables must be set"


class YDBSession:
    def __init__(self):
        self._driver = ydb.Driver(endpoint=YDB_ENDPOINT, database=YDB_PATH)
        self._driver.wait(fail_fast=True, timeout=5)
        self._session = self._driver.table_client.session().create()

    def _request_ydb_query(self, yql_query):
        settings = \
            ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)

        result = self._session.transaction().execute(
            yql_query,
            commit_tx=True,
            settings=settings
        )
        return result

    def _write_db_house(self, house_info: dict):
        houses_table_address = '"' + house_info["Адрес"] + '"'

        # Dict -> Json string for YQL query (see below)
        houses_table_additional_info = json.dumps(house_info, indent=4)

        if "_meta_company_info" in house_info.keys():
            houses_table_company_name = house_info["_meta_company_info"]["Наименование"]
            houses_table_company_name = '"' + houses_table_company_name + '"'
        else:
            houses_table_company_name = "null"

        self._request_ydb_query(f"""
            REPLACE INTO houses (address, additional_info, company_name) VALUES
                (
                    {houses_table_address},
                    CAST(@@{houses_table_additional_info}@@ AS Json), 
                    {houses_table_company_name}
                );
        """)

    def _write_db_company(self, company_info: dict):
        companies_table_company_name = '"' + company_info["Наименование"] + '"'
        companies_table_additional_info = json.dumps(company_info, indent=4)

        self._request_ydb_query(f"""
            REPLACE INTO companies (name, additional_info) VALUES
                (
                    {companies_table_company_name},
                    CAST(@@{companies_table_additional_info}@@ AS Json)
                );
        """)

    def search_in_database(self, table: str, search_value: str) -> list:
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
        return self._request_ydb_query(query)

    def update_database_with_parser(self):
        house_id = 1
        houses_urls = get_houses_urls_for_city(TARGET_HOUSES_TABLE_URL)

        for house_url in houses_urls:
            current_house_info = get_house_info(house_url)
            self._write_db_house(current_house_info)

            if "_meta_company_info" in current_house_info.keys():
                company_info = current_house_info["_meta_company_info"]
                self._write_db_company(company_info)

            house_id += 1
