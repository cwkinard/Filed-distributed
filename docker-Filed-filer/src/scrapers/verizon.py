from bs4 import BeautifulSoup
import requests
import re
import logging
from datetime import datetime
import os
from scraperbase import ScraperBase
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from utility import wait_for_page_load



LOGIN_PAGE = 'https://www.verizonwireless.com'


class Scraper(ScraperBase):

    def __init__(self, *args, **kwargs):
        super(Scraper, self).__init__(*args, **kwargs)

    def _login(self):
	
	browser = webdriver.Remote(
   	   command_executor='http://selenium:4444/wd/hub',
   	   desired_capabilities=DesiredCapabilities.PHANTOMJS)
	
	browser.get(LOGIN_PAGE)

	login = browser.find_element_by_id('IDToken1')
        login.send_keys(self.username)

	with wait_for_page_load(browser):
            login.send_keys(Keys.RETURN)

	self._logger.debug('Secret Question:' in browser.page_source)
	browser.get_screenshot_as_file('/home/pi/Dev/pass2.png')
	if 'Secret Question:' in browser.page_source:

	    question_page = BeautifulSoup(browser.page_source, 'html.parser')
	    question = question_page.find('div', {'class':'col-xs-12 col-sm-6'}).find_all('p')[2].text.split(':')[1]
	
	    self._logger.info(question)

	    answer = browser.find_element_by_id('IDToken1')
	    answer.send_keys(self.qa[question])
	    
	    with wait_for_page_load(browser):
	        answer.send_keys(Keys.RETURN)

	password = browser.find_element_by_id('IDToken2')
        password.send_keys(self.password)

	with wait_for_page_load(browser):
            password.send_keys(Keys.RETURN)

	# Transfer session to python-requests
	for cookie in browser.get_cookies():
    	    c = {cookie['name']: cookie['value']}
    	    self.s.cookies.update(c)	

	browser.close()

	self._logger.info("Logged In")
    
    def _get_statement_rows(self):

	# View statement history
        statement_url = 'https://ebillpay.verizonwireless.com/vzw/accountholder/digitalocker/MessageCenter_UIM.action'
        
	headers = {
          'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'
        }	

	self.res = self.s.get(statement_url, headers=headers)
	#self._logger.debug(self.res.text)
        statement_html = BeautifulSoup(self.res.text, 'html.parser')
        rows = statement_html.find_all('tr')
        return rows

    def scrape(self, account, drive_date):
	
	self._logger.info("Starting scrape for account '%s' ", account)

	rows = self._get_statement_rows()

	for row in rows:	
	    cols = row.find_all('td')
            link = cols[0].find('a').get('href')
            date_raw = cols[5].text
	    statement_date = datetime.strptime(date_raw, "%m/%d/%Y").date()
	
	    self._logger.debug("Statement Date: '%s', Drive Date: '%s' ", statement_date, drive_date)

	    # Break when dates match
	    if statement_date <= drive_date:
		break
	    	
	    # Download statement
	    statement_url = 'https://ebillpay.verizonwireless.com'
	    statement_url += link
	    
	    headers = {
              'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36'
            }
	
	    file = self.s.get(statement_url, headers=headers) 	

	    # Save statement
	    self._save(file, statement_date)
	
	return
	    

    def hasNew(self, account, date):
	
	rows = self._get_statement_rows()
 
        cols = rows[0].find_all('td')
        date_raw = cols[5].text
        latest_date = datetime.strptime(date_raw, "%m/%d/%Y").date()

	if latest_date > date:
	    self._logger.info("New statement(s) found")
	    return True
	else:
	    self._logger.info("No new statement(s) found")
	    return False



   
