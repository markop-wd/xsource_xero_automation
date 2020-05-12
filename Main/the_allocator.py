from Main import logic

from selenium.webdriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager

driver = Chrome(ChromeDriverManager().install())
driver.maximize_window()


# noinspection PyBroadException
def runner():
    try:
        account_payer = logic.AccountPay(driver)
        account_payer.log_in()
        log.info('Moving to org switching')
        account_payer.organisation_name = input('Please enter the organisation name: ')
        account_payer.org_switch()
        log.info('Navigated to: ' + str(account_payer.current_org) + ', moving on to extraction of links')
        account_payer.href_extraction()
        log.info('Got the links, going through each')
        account_payer.invoice_pay()
        log.info('Looped over all the links')
        input('Finished, press enter to quit')
        driver.quit()
    except:
        logging.exception('Critical Failure')
        input('An error occured press enter to quit the application')
        driver.quit()


if __name__ == '__main__':
    import logging.config

    logging.config.fileConfig('log_settings.ini', disable_existing_loggers=False)
    log = logging.getLogger(__name__)

    runner()
