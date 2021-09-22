import traceback

from selenium.webdriver import Chrome
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait as WdWait
from selenium.common import exceptions
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By


def element_clicker(driver: Chrome, web_element: WebElement = None, css_selector: str = ''):
    if css_selector:
        try:
            element = WdWait(driver, 10).until(
                ec.element_to_be_clickable((By.CSS_SELECTOR, css_selector)))
        except exceptions.TimeoutException:
            raise exceptions.ElementNotInteractableException(
                'Element not clickable after 10 seconds')
        except exceptions.NoSuchElementException:
            raise exceptions.NoSuchElementException(
                f'No element found with css selector: {css_selector}')
        except Exception as e:
            print(traceback.format_exc())
            raise e
        else:
            try:
                element.click()
            except exceptions.ElementClickInterceptedException:
                driver.execute_script('arguments[0].click();', element)
            except Exception as e:
                print(traceback.format_exc())
                raise e

    elif web_element:
        try:
            web_element.click()
        except exceptions.ElementClickInterceptedException:
            try:
                driver.execute_script('arguments[0].click();', web_element)
            except exceptions.JavascriptException:
                driver.execute_script('arguments[0].click();', web_element)
            finally:
                return True
        except exceptions.ElementNotInteractableException:
            return False
        except exceptions.StaleElementReferenceException:
            return False

        except Exception as e:
            print(traceback.format_exc())
            return False
        else:
            return True


def element_waiter(driver: Chrome, css_selector: str, url: str = '') -> WebElement:
    """
    Pass in a css selector and a URL and this will retry finding it
    """
    condition = ec.presence_of_element_located((By.CSS_SELECTOR, css_selector))
    try:
        ret_el = WdWait(driver, 10).until(condition)
    except exceptions.TimeoutException:
        if url:
            driver.get(url)
        else:
            driver.refresh()

        try:
            ret_el = WdWait(driver, 10).until(condition)
        except exceptions.TimeoutException:
            if url:
                driver.get(url)
            else:
                driver.refresh()
            ret_el = WdWait(driver, 20).until(condition)

    return ret_el


def login_element_waiter(driver: Chrome):
    """
    Pass in a css selector and a URL and this will retry finding it
    """
    condition = ec.presence_of_element_located((By.ID, 'root'))
    try:
        WdWait(driver, 10).until(condition)
    except exceptions.TimeoutException:
        driver.refresh()
        if "login.xero.com" in driver.current_url:
            input("Login failed, please log in again.\nPress enter once finished")
            try:
                WdWait(driver, 10).until(condition)
            except exceptions.TimeoutException:
                driver.refresh()
                if "login.xero.com" in driver.current_url:
                    LoginException('Log in failed multiple times, closing the application')


class LoginException(Exception):
    def __init__(self, message):
        super().__init__(message)


class OrgFinderException(Exception):
    def __init__(self, message):
        super().__init__(message)