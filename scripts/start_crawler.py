"""
Crawler entry point intentionally disabled.

The project now reads existing house records from the configured MySQL
database/table and should not start a crawler during local execution.
"""


def start_spider(city=None, pages=None):
    print('Crawler is disabled. The project reads existing data from house_info.')
    print('Import new data into the MySQL database configured in config/database.yml.')
    return 0


if __name__ == '__main__':
    start_spider()
