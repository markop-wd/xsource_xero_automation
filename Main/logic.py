from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait as wd_wait
from selenium.common import exceptions
import logging

from time import sleep
import csv

TOTAL_LIST = []

logger = logging.getLogger(__name__)

with open('compare_csv.csv', mode='w', newline='') as comparer:
    field_names = ['Link', 'More To Allocate', 'Error']
    comparer = csv.DictWriter(comparer, fieldnames=field_names)

    comparer.writeheader()


class AccountPay:

    def __init__(self, driver):
        self.clickerino = False
        self.driver = driver
        self.organisation_name = ''
        self.current_org = ''

    def log_in(self):
        self.driver.get('https://login.xero.com/')
        # test_login(self.driver)
        input("Please press enter once you login")

    def org_switch(self):
        try:
            wd_wait(self.driver, 10).until(ec.presence_of_element_located((By.ID, 'root')))
        except exceptions.TimeoutException:
            self.driver.refresh()
            if "login.xero.com" in self.driver.current_url:
                logger.warning("Login failed, please log in again")
                input("Press enter once finished")
                try:
                    wd_wait(self.driver, 20).until(ec.presence_of_element_located((By.ID, 'root')))
                except exceptions.TimeoutException:
                    self.driver.refresh()
                    if "login.xero.com" in self.driver.current_url:
                        logger.warning("Login failed, please log in again")
                        input("Press enter once finished")
                    wd_wait(self.driver, 20).until(ec.presence_of_element_located((By.ID, 'root')))

        org_button_text = wd_wait(self.driver, 10).until(
            ec.presence_of_element_located((By.CLASS_NAME, 'xrh-appbutton--text'))).text
        if org_button_text.lower() != self.organisation_name.lower():
            wd_wait(self.driver, 10).until(
                ec.element_to_be_clickable((By.CLASS_NAME, 'xrh-button.xrh-appbutton'))).click()
            #           self.driver.find_element_by_class_name('xrh-button.xrh-appbutton').click()
            wd_wait(self.driver, 10).until(
                ec.element_to_be_clickable((By.CLASS_NAME, 'xrh-button.xrh-verticalmenuitem'
                                                           '--body'))).click()
            try:
                wd_wait(self.driver, 6).until(ec.presence_of_element_located(
                    (By.CLASS_NAME, 'xrh-orgsearch--input'))).send_keys(self.organisation_name.lower())
            except exceptions.TimeoutException:
                for link_item in self.driver.find_elements_by_class_name('xrh-menuitem-orgpractice'):
                    if link_item.text == self.organisation_name:
                        link_item.click()
            else:
                try:
                    wd_wait(self.driver, 5).until(
                        ec.presence_of_element_located((By.CLASS_NAME, 'xrh-menuitem-orgpractice')))
                except exceptions.TimeoutException:
                    raise Exception('Cannot find', self.organisation_name)
                else:
                    sleep(2)
                    orgs = self.driver.find_elements_by_class_name('xrh-menuitem-orgpractice')
                    org_names = [orggg.text for orggg in
                                 self.driver.find_elements_by_class_name('xrh-menuitem-orgpractice')]
                for element in orgs:
                    if element.text.lower() == self.organisation_name.lower():
                        self.driver.find_element_by_class_name('xrh-menuitem-orgpractice').click()
                        sleep(5)
                        self.current_org = wd_wait(self.driver, 25).until(ec.presence_of_element_located(
                            (By.CLASS_NAME, 'xrh-appbutton--text'))).text
                        if self.current_org.lower() != self.organisation_name.lower():
                            raise Exception('Couldn\'t log in to', self.organisation_name)
                        break
                else:
                    print('No exact match with that organisation name - did you mean?')
                    [print("  " + org_name) for org_name in org_names if
                     self.organisation_name.lower() in org_name.lower()]
                    self.organisation_name = input('Please re-input the exact organisation name: ').lower()
                    for organis in self.driver.find_elements_by_class_name('xrh-menuitem-orgpractice'):
                        if self.organisation_name.lower() == organis.text.lower():
                            organis.click()
                            sleep(5)
                            self.current_org = wd_wait(self.driver, 25).until(ec.presence_of_element_located(
                                (By.CLASS_NAME, 'xrh-appbutton--text'))).text
                            if self.current_org.lower() != self.organisation_name.lower():
                                raise Exception('Couldn\'t log in to', self.organisation_name)
                            break
                    else:
                        self.driver.refresh()
                        self.org_switch()
        else:
            self.current_org = self.organisation_name

    # TODO - Add a name checker
    def href_extraction(self):

        self.driver.get('https://go.xero.com/AccountsPayable/Search.aspx?invoiceStatus=INVOICESTATUS%2fAUTHORISED')
        try:
            wd_wait(self.driver, 10).until(ec.presence_of_element_located((By.ID, 'frmMain')))
        except exceptions.TimeoutException:
            self.driver.get('https://go.xero.com/AccountsPayable/Search.aspx?invoiceStatus=INVOICESTATUS%2fAUTHORISED')
            try:
                wd_wait(self.driver, 10).until(ec.presence_of_element_located((By.ID, 'frmMain')))
            except exceptions.TimeoutException:
                self.driver.get(
                    'https://go.xero.com/AccountsPayable/Search.aspx?invoiceStatus=INVOICESTATUS%2fAUTHORISED')
                wd_wait(self.driver, 30).until(ec.presence_of_element_located((By.ID, 'frmMain')))

        # Get the number of items that need to be paid out
        total_items = int(self.driver.find_element_by_id('total-paged-items').text)

        if total_items // 200 > 0:
            # calculates the number of pages based on the number of items, taking in consideration that pages will include 200 items
            page_count = total_items // 200
            # create a list of page numbers to pass to the first self.driver.get below
            page_num = list(range(1, page_count + 2))
            for pg_num in page_num:
                current_list = []
                self.driver.get(
                    f'https://go.xero.com/AccountsPayable/Search.aspx?invoiceStatus=INVOICESTATUS%2fAUTHORISED&graphSearch=False&dateWithin=any&page={pg_num}&PageSize=200&orderBy=PaidToName&direction=ASC')
                try:
                    table = wd_wait(self.driver, 10).until(
                        ec.presence_of_element_located((By.CSS_SELECTOR, 'table > tbody')))
                except exceptions.TimeoutException:
                    self.driver.get(
                        f'https://go.xero.com/AccountsPayable/Search.aspx?invoiceStatus=INVOICESTATUS%2fAUTHORISED&graphSearch=False&dateWithin=any&page={pg_num}&PageSize=200&orderBy=PaidToName&direction=ASC')
                    try:
                        table = wd_wait(self.driver, 10).until(
                            ec.presence_of_element_located((By.CSS_SELECTOR, 'table > tbody')))
                    except exceptions.TimeoutException:
                        self.driver.get(
                            f'https://go.xero.com/AccountsPayable/Search.aspx?invoiceStatus=INVOICESTATUS%2fAUTHORISED&graphSearch=False&dateWithin=any&page={pg_num}&PageSize=200&orderBy=PaidToName&direction=ASC')
                        table = wd_wait(self.driver, 10).until(
                            ec.presence_of_element_located((By.CSS_SELECTOR, 'table > tbody')))
                try:
                    for icon in table.find_elements_by_class_name('icons.credit'):
                        current_list.append(icon.find_element_by_xpath('./../../td/a').get_attribute('href'))
                except exceptions.NoSuchElementException:
                    logger.warning(f'Either no credit notes or unable to find them')
                    continue

                TOTAL_LIST.append(current_list)
        else:
            current_list = []
            self.driver.get(
                f'https://go.xero.com/AccountsPayable/Search.aspx?invoiceStatus=INVOICESTATUS%2fAUTHORISED&graphSearch=False&dateWithin=any&page=1&PageSize=200&orderBy=PaidToName&direction=ASC')
            try:
                table = wd_wait(self.driver, 10).until(
                    ec.presence_of_element_located((By.CSS_SELECTOR, 'table > tbody')))
            except exceptions.TimeoutException:
                self.driver.get(
                    f'https://go.xero.com/AccountsPayable/Search.aspx?invoiceStatus=INVOICESTATUS%2fAUTHORISED&graphSearch=False&dateWithin=any&page=1&PageSize=200&orderBy=PaidToName&direction=ASC')
                try:
                    table = wd_wait(self.driver, 10).until(
                        ec.presence_of_element_located((By.CSS_SELECTOR, 'table > tbody')))
                except exceptions.TimeoutException:
                    self.driver.get(
                        f'https://go.xero.com/AccountsPayable/Search.aspx?invoiceStatus=INVOICESTATUS%2fAUTHORISED&graphSearch=False&dateWithin=any&page=1&PageSize=200&orderBy=PaidToName&direction=ASC')
                    table = wd_wait(self.driver, 10).until(
                        ec.presence_of_element_located((By.CSS_SELECTOR, 'table > tbody')))
            try:
                for icon in table.find_elements_by_class_name('icons.credit'):
                    current_list.append(icon.find_element_by_xpath('./../../td/a').get_attribute('href'))
            except exceptions.NoSuchElementException:
                logger.warning(f'Either no credit notes or unable to find them')

            TOTAL_LIST.append(current_list)

    def invoice_pay(self):
        import re

        for href_list in TOTAL_LIST:
            for href in href_list:
                self.driver.get(href)
                more_to_allocate = False
                try:
                    wd_wait(self.driver, 10).until(ec.presence_of_element_located((By.CLASS_NAME, 'document.invoice')))
                except exceptions.TimeoutException:
                    self.driver.get(href)
                    try:
                        wd_wait(self.driver, 10).until(
                            ec.presence_of_element_located((By.CLASS_NAME, 'document.invoice')))
                    except exceptions.TimeoutException:
                        try:
                            wd_wait(self.driver, 20).until(
                                ec.presence_of_element_located((By.CLASS_NAME, 'document.invoice')))
                        except exceptions.TimeoutException:
                            # print('Error on loading page, continuing')
                            logger.error(f"couldn't load {href}")
                            continue

                if 'Credit Note' in str(self.driver.find_element_by_id('title').text):
                    try:
                        allocate_credit_btn = self.driver.find_element_by_css_selector(
                            'dd > ul > li > a[href*="/Credits/Allocate"]')
                    except exceptions.NoSuchElementException:
                        continue
                    else:
                        self.driver.get(allocate_credit_btn.get_attribute('href'))
                        try:
                            wd_wait(self.driver, 30).until(
                                ec.presence_of_element_located((By.CLASS_NAME, 'document.allocate.forms')))
                        except exceptions.TimeoutException:
                            self.driver.get(allocate_credit_btn.get_attribute('href'))
                            try:
                                wd_wait(self.driver, 30).until(
                                    ec.presence_of_element_located((By.CLASS_NAME, 'document.allocate.forms')))
                            except exceptions.TimeoutException:
                                # print('Error on loading page, continuing')
                                logger.error(f"Couldn't load:{allocate_credit_btn.get_attribute('href')}")
                                continue

                        # here
                        remaining_credit_text = self.driver.find_element_by_id('BalanceDue').get_attribute(
                            'innerText')
                        remaining_credit_text = re.sub(',', '', remaining_credit_text)
                        remaining_credit = round(float(remaining_credit_text), 2)
                        bill_row_array = self.driver.find_element_by_id(
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
                                logger.error(f'Went into a negative value when filling{self.driver.current_url}')
                                break

                        self.driver.find_element_by_class_name('large.green').click()
                        # input('Allocate?')

                        try:
                            wd_wait(self.driver, 10).until(
                                ec.presence_of_element_located((By.CLASS_NAME, 'document.invoice')))
                        except exceptions.TimeoutException:
                            logger.error('Unable to re-load the invoice page for confirmation.')

                            with open('compare_csv.csv', mode='a', newline='') as checker:
                                fieldnames = ['Link', 'More To Allocate', 'Error']
                                checker = csv.DictWriter(checker, fieldnames=fieldnames)

                                checker.writerow(
                                    {"Link": href, "More To Allocate": None, "Error": True})

                        else:
                            try:
                                self.driver.find_element_by_css_selector(
                                    'dd > ul > li > a[href*="/Credits/Allocate"]')
                            except exceptions.NoSuchElementException:
                                pass
                            else:
                                more_to_allocate = True

                            with open('compare_csv.csv', mode='a', newline='') as checker:
                                fieldnames = ['Link', 'More To Allocate', 'Error']
                                checker = csv.DictWriter(checker, fieldnames=fieldnames)

                                checker.writerow(
                                    {"Link": href, "More To Allocate": more_to_allocate, "Error": None})

                            logger.info(f'Allocated {self.driver.current_url}')
