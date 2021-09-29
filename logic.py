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

from helper_funcs import element_clicker, element_waiter, login_element_waiter, LoginException
from urls import INVOICE_STATUS, PAGE_SEARCH

logger = logging.getLogger(__name__)


def csv_append(href, more_to_allocate, error=None):
    """
    Simple function that writes to a .csv
    """
    with open('compare_csv.csv', mode='a', newline='', encoding='UTF-8') as checker:
        fieldnames = ['Link', 'More To Allocate', 'Error']
        checker = csv.DictWriter(checker, fieldnames=fieldnames)

        checker.writerow(
            {"Link": href, "More To Allocate": more_to_allocate, "Error": error})


def log_in(driver: Chrome):
    """
    Simple log in function utilizing a helper
    :param driver:
    :return:
    """
    driver.get('https://login.xero.com/')
    input("Please press enter once you login")
    try:
        login_element_waiter(driver)
    except LoginException:
        logger.warning('Log in failed multiple times, closing the application')
        driver.quit()


def org_switch(driver: Chrome, org_name: str) -> str:
    """
    Changing organizations within Xero
    :param driver:
    :param org_name: Organization name to search for
    :return current_org: An empty string if no organization is found, otherwise the org name
    """
    current_org = ''
    org_button_text = WdWait(driver, 10).until(
        ec.presence_of_element_located((By.CLASS_NAME, 'xrh-appbutton--text'))).text
    # If the name of the current organization does not match the element that identifies the org in xero move on
    if org_name.lower() != org_button_text.lower:
        element_clicker(driver, css_selector='.xrh-button.xrh-appbutton')
        element_clicker(driver, css_selector='.xrh-button.xrh-verticalmenuitem--body')
        try:
            # Try using the input element to search for an org
            WdWait(driver, 6).until(ec.presence_of_element_located(
                (By.CLASS_NAME, 'xrh-orgsearch--input'))).send_keys(org_name.lower())
        except exceptions.TimeoutException:
            # If there is no input element for search, try searching through the available org list
            for link_item in driver.find_elements_by_class_name('xrh-menuitem-orgpractice'):
                if link_item.text.lower() == org_name.lower():
                    element_clicker(driver, web_element=link_item)
        else:
            # find all the elements that are returned after typing the org name
            WdWait(driver, 5).until(
                ec.presence_of_element_located((By.CLASS_NAME, 'xrh-menuitem-orgpractice')))
            sleep(2)
            available_orgs = driver.find_elements_by_class_name('xrh-menuitem-orgpractice')
            # Store org names in case we don't find a match and want to provide user with org names
            org_names = [orggg.text for orggg in available_orgs]

            for individual_org in available_orgs:
                if individual_org.text.lower() == org_name.lower():
                    element_clicker(driver, web_element=individual_org)
                    sleep(5)
                    WdWait(driver, 25).until(ec.presence_of_element_located(
                        (By.CLASS_NAME, 'xrh-appbutton--text')))
                    current_org = org_name
                    break
            else:

                matching_org_names = [_org_name for _org_name in org_names if
                                      org_name.lower() in _org_name.lower()]
                if matching_org_names:
                    print('No exact match with that organisation name - did you mean?')
                    print(matching_org_names)

    else:
        current_org = org_name

    return current_org


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



def invoice_pay(driver: Chrome, total_list: list) -> None:
    """
    Takes all the invoice urls and completes the action/calculations needed to pay them
    :param driver:
    :param total_list:
    :return:
    """
    for href in total_list:
        driver.get(href)
        _load_el = element_waiter(driver, css_selector='.document.invoice', url=href)
        if not _load_el:
            logger.error("could not load %s", href)
            continue

        if 'Credit Note' in str(driver.find_element_by_id('title').text):
            try:
                allocate_credit_btn = driver.find_element_by_css_selector(
                    'dd > ul > li > a[href*="/Credits/Allocate"]')
            except exceptions.NoSuchElementException:
                # The allocate credit button was not found meaning there is nothing to allocate, skip
                continue
            else:
                allocate_url = allocate_credit_btn.get_attribute('href')
                driver.get(allocate_url)
                _load_el = element_waiter(driver, css_selector='.document.allocate.forms', url=allocate_url)

                if not _load_el:
                    logger.error("Could not load: %s", allocate_url)
                    continue

                allocation_input(driver)

                allocation_finalize(driver, href)



def allocation_input(driver: Chrome):
    """
    The function that is used to handle the input elements and it also houses the logic for allocation calculations
    """
    # Remaining credit is how much we have available for allocation
    remaining_credit_text = driver.find_element_by_id('BalanceDue').get_attribute('innerText')
    # Remove commas that are used to split above three digit figures e.g. 1,342
    remaining_credit_text = re.sub(',', '', remaining_credit_text)
    remaining_credit = round(float(remaining_credit_text), 2)
    # Find all the rows with the input els where the funds need to be allocated
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


def allocation_finalize(driver: Chrome, href: str):
    """
    Wait for proper elements to load up, and log the results into the console and the csv
    """
    # allocate (finalize) button
    element_clicker(driver, css_selector='.large.green')
    try:
        WdWait(driver, 10).until(
            ec.presence_of_element_located((By.CLASS_NAME, 'document.invoice')))
    except exceptions.TimeoutException:
        logger.error('Unable to re-load the invoice page for confirmation.')
        csv_append(href, more_to_allocate=False, error=True)

    else:
        try:
            driver.find_element_by_css_selector(
                'dd > ul > li > a[href*="/Credits/Allocate"]')
        except exceptions.NoSuchElementException:
            more_to_allocate = False
        else:
            more_to_allocate = True

        csv_append(href, more_to_allocate)

        logger.info('Allocated %s', driver.current_url)
