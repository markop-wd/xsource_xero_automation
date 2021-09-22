"""
Main logic of the automation
"""
import csv
import re
import logging
from time import sleep

from selenium.common import exceptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait as WdWait
from selenium.webdriver import Chrome

from helper_funcs import element_clicker, element_waiter, login_element_waiter, LoginException, OrgFinderException
from urls import INVOICE_STATUS, PAGE_SEARCH

logger = logging.getLogger(__name__)


def log_in(driver: Chrome):
    """
    Simple log in function utilizing a helper
    :param driver:
    :return:
    """
    driver.get('https://login.xero.com/')
    # TODO - Extract the three WdWaits with try except in a pattern
    input("Please press enter once you login")
    try:
        login_element_waiter(driver)
    except LoginException:
        logger.warning('Log in failed multiple times, closing the application')
        driver.quit()


# TODO Refactor and recheck
def org_switch(driver: Chrome, org_name: str):
    """
    Changing organizations within Xero
    :param driver:
    :param org_name:
    :return:
    """
    current_org = ''
    org_button_text = WdWait(driver, 10).until(
        ec.presence_of_element_located((By.CLASS_NAME, 'xrh-appbutton--text'))).text
    if org_name.lower() != org_button_text.lower:
        element_clicker(driver, css_selector='.xrh-button.xrh-appbutton')
        element_clicker(driver, css_selector='.xrh-button.xrh-verticalmenuitem--body')
        try:
            WdWait(driver, 6).until(ec.presence_of_element_located(
                (By.CLASS_NAME, 'xrh-orgsearch--input'))).send_keys(org_name.lower())
        except exceptions.TimeoutException:
            for link_item in driver.find_elements_by_class_name('xrh-menuitem-orgpractice'):
                if link_item.text == org_name:
                    element_clicker(driver, web_element=link_item)
        else:
            try:
                WdWait(driver, 5).until(
                    ec.presence_of_element_located((By.CLASS_NAME, 'xrh-menuitem-orgpractice')))
            except exceptions.TimeoutException as exc:
                raise OrgFinderException(f'Cannot find {org_name}') from exc
            else:
                sleep(2)
                orgs = driver.find_elements_by_class_name('xrh-menuitem-orgpractice')
                org_names = [orggg.text for orggg in
                             driver.find_elements_by_class_name('xrh-menuitem-orgpractice')]
            for element in orgs:
                if element.text.lower() == org_name.lower():
                    element_clicker(driver, css_selector='.xrh-menuitem-orgpractice')
                    sleep(5)
                    current_org = WdWait(driver, 25).until(ec.presence_of_element_located(
                        (By.CLASS_NAME, 'xrh-appbutton--text'))).text
                    if current_org.lower() != org_name.lower():
                        raise OrgFinderException(f'Cannot find {org_name}')
                    break
            else:

                matching_org_names = [_org_name for _org_name in org_names if
                                      org_name.lower() in _org_name.lower()]
                if matching_org_names:
                    print('No exact match with that organisation name - did you mean?')
                    for org in matching_org_names:
                        print(f"  {org}")

                org_name = input('Please re-input the exact organisation name: ').lower()
                for organis in driver.find_elements_by_class_name('xrh-menuitem-orgpractice'):
                    if org_name.lower() == organis.text.lower():
                        element_clicker(driver, web_element=organis)
                        sleep(5)
                        current_org = WdWait(driver, 25).until(ec.presence_of_element_located(
                            (By.CLASS_NAME, 'xrh-appbutton--text'))).text
                        if current_org.lower() != org_name.lower():
                            raise OrgFinderException(f'Cannot find {org_name}')
                        break
                else:
                    raise OrgFinderException(f'Cannot find {org_name}')

    else:
        current_org = org_name

    return current_org


# TODO - Refactor and recheck
def invoice_pay(driver: Chrome, total_list: list) -> None:
    """
    Takes all the invoice urls and completes the action/calculations needed to pay them
    :param driver:
    :param total_list:
    :return:
    """
    for href in total_list:
        driver.get(href)
        more_to_allocate = False
        _load_el = element_waiter(driver, css_selector='.document.invoice', url=href)
        if not _load_el:
            logger.error("could not load %s", href)
            continue

        if 'Credit Note' in str(driver.find_element_by_id('title').text):
            try:
                allocate_credit_btn = driver.find_element_by_css_selector(
                    'dd > ul > li > a[href*="/Credits/Allocate"]')
            except exceptions.NoSuchElementException:
                continue
            else:
                allocate_url = allocate_credit_btn.get_attribute('href')
                driver.get(allocate_url)
                _load_el = element_waiter(driver, css_selector='.document.allocate.forms', url=allocate_url)

                if not _load_el:
                    logger.error("Could not load: %s", allocate_url)
                    continue

                remaining_credit_text = driver.find_element_by_id('BalanceDue').get_attribute(
                    'innerText')
                remaining_credit_text = re.sub(',', '', remaining_credit_text)
                remaining_credit = round(float(remaining_credit_text), 2)
                bill_row_array = driver.find_element_by_id(
                    'creditLineItems').find_elements_by_tag_name(
                    'tr')
                for bill_row in bill_row_array:

                    row_due_amount = round(
                        float(bill_row.find_element_by_css_selector('td > input').get_attribute('value')), 2)

                    if remaining_credit > 0:
                        if row_due_amount - remaining_credit >= 0:
                            bill_row.find_element_by_css_selector(
                                'td > div > span > input').send_keys(
                                str(remaining_credit))
                            remaining_credit -= remaining_credit

                        elif row_due_amount - remaining_credit < 0:
                            bill_row.find_element_by_css_selector(
                                'td > div > span > input').send_keys(str(row_due_amount))
                            remaining_credit -= row_due_amount

                    elif remaining_credit < 0:
                        # print("Calculation Error, didn't fill in", href)
                        logger.error('Went into a negative value when filling %s', driver.current_url)
                        break

                # allocate (finalize) button
                element_clicker(driver, css_selector='.large.green')

                try:
                    WdWait(driver, 10).until(
                        ec.presence_of_element_located((By.CLASS_NAME, 'document.invoice')))
                except exceptions.TimeoutException:
                    logger.error('Unable to re-load the invoice page for confirmation.')

                    with open('compare_csv.csv', mode='a', newline='', encoding='UTF-8') as checker:
                        fieldnames = ['Link', 'More To Allocate', 'Error']
                        checker = csv.DictWriter(checker, fieldnames=fieldnames)

                        checker.writerow(
                            {"Link": href, "More To Allocate": None, "Error": True})

                else:
                    try:
                        driver.find_element_by_css_selector(
                            'dd > ul > li > a[href*="/Credits/Allocate"]')
                    except exceptions.NoSuchElementException:
                        pass
                    else:
                        more_to_allocate = True

                    with open('compare_csv.csv', mode='a', newline='', encoding='UTF-8') as checker:
                        fieldnames = ['Link', 'More To Allocate', 'Error']
                        checker = csv.DictWriter(checker, fieldnames=fieldnames)

                        checker.writerow(
                            {"Link": href, "More To Allocate": more_to_allocate, "Error": None})

                    logger.info('Allocated %s', driver.current_url)


def href_extraction(driver: Chrome):
    """
    Method in charge of collecting all the urls for invoices to be paid
    :return:
    """
    total_list = []
    driver.get(INVOICE_STATUS)
    element_waiter(driver, css_selector='#frmMain', url=INVOICE_STATUS)

    # Get the number of items that need to be paid out
    total_items = int(driver.find_element_by_id('total-paged-items').text) - 1

    if (total_items // 200) > 0:
        # calculates the number of pages based on the number of items, taking in consideration that pages will
        # include 200 items
        page_count = total_items // 200
        # create a list of page numbers to pass to the first driver.get below
        page_num = list(range(1, page_count + 2))
        for pg_num in page_num:
            driver.get(PAGE_SEARCH.format(pg_num))
            table = element_waiter(driver, css_selector='table > tbody', url=PAGE_SEARCH.format(pg_num))
            try:
                for icon in table.find_elements_by_class_name('icons.credit'):
                    total_list.append(icon.find_element_by_xpath('./../../td/a').get_attribute('href'))
            except exceptions.NoSuchElementException:
                logger.warning('Either no credit notes or unable to find them')
                continue

    else:
        driver.get(PAGE_SEARCH.format(1))
        table = element_waiter(driver, css_selector='table > tbody', url=PAGE_SEARCH.format(1))
        try:
            for icon in table.find_elements_by_class_name('icons.credit'):
                total_list.append(icon.find_element_by_xpath('./../../td/a').get_attribute('href'))
        except exceptions.NoSuchElementException:
            logger.warning('Either no credit notes or unable to find them')

    return total_list
