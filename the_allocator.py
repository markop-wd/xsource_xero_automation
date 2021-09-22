"""
Main business logic of the automation
"""
import csv

from selenium.webdriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager

from logic import log_in, org_switch, href_extraction, invoice_pay


with open('compare_csv.csv', mode='w', newline='', encoding='UTF-8') as compare_csv:
    field_names = ['Link', 'More To Allocate', 'Error']
    compare_csv = csv.DictWriter(compare_csv, fieldnames=field_names)

    compare_csv.writeheader()


driver = Chrome(ChromeDriverManager().install())
driver.maximize_window()


def runner():
    """
    Just a basic caller
    :return:
    """
    try:
        log_in(driver)
        log.info('Moving to org switching')
        input_org_name = input('Please enter the organisation name: ')
        current_org = org_switch(driver, org_name=input_org_name)
        log.info('Navigated to: %s, moving on to extraction of links', str(current_org))
        href_list = href_extraction(driver)
        log.info('Got the links, going through each')
        invoice_pay(driver, href_list)
        log.info('Looped over all the links')
        input('Finished, press enter to quit')
        driver.quit()
    except:
        logging.exception('Critical Failure')
        driver.quit()


if __name__ == '__main__':
    import logging.config

    logging.config.fileConfig('log_settings.ini', disable_existing_loggers=False)
    log = logging.getLogger(__name__)

    runner()
