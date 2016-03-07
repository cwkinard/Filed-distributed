from bs4 import BeautifulSoup
import requests
import re
import logging
from datetime import datetime
import os
from random import randint
import time
from scraperbase import ScraperBase

LOGIN_PAGE = 'https://mfasa.chase.com/auth/fcc/login'


class Scraper(ScraperBase):

    def __init__(self, *args, **kwargs):
        super(Scraper, self).__init__(*args, **kwargs)

    def _login(self):
	
	# Create random number
	rand5 = str(randint(10000,99999))
	rand3 = str(randint(100,999))
	reqid = rand5 + str(int(time.time())) + rand3
	
	self.res = self.s.get('https://mfasa.chase.com/auth/fcc/randomize?auth_reqid=' + reqid)

	form = BeautifulSoup(self.res.text, 'html.parser')

	data = {} 

	for input in form.find_all('input'):
	    data[input.get('name')] = input.get('value')
	    
	    id = input.get('id')
	    if id == 'userId':
		data[input.get('name')] = self.username
	    elif id == 'passwd':
		data[input.get('name')] = self.password
	    elif id == 'passwd_org':
		data[input.get('name')] = self.password
	    elif id == 'otp':
		data[input.get('name')] = 'RBGLogon'
	    elif id == 'LOB':
		data[input.get('name')] = 'LOB=RBGLogon'
	    elif id == 'deviceSignature':
		data[input.get('name')] = """{"navigator":{"vendorSub":"","productSub":"20030107","vendor":"Google Inc.","maxTouchPoints":10,"hardwareConcurrency":4,"appCodeName":"Mozilla","appName":"Netscape","appVersion":"5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36","platform":"Win32","product":"Gecko","userAgent":"Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36","language":"en-US","onLine":true,"cookieEnabled":true},"plugins":[{"name":"Macromedia Shockwave Flash","version":"20.0"}],"screen":{"availHeight":900,"availWidth":1706,"colorDepth":24,"height":960,"pixelDepth":24,"width":1706},"extra":{"javascript_ver":"2.0","timezone":300}}"""
	    elif id == 'deviceCookie':
		data[input.get('name')] = 'adtoken'
	    elif id == 'Referer':
		data[input.get('name')] = 'https://www.chase.com/'	 
	    elif id == 'siteId':
		data[input.get('name')] = 'COL'

	self.res = self.s.post(LOGIN_PAGE, data=data)

	self._logger.debug(data)
	self._logger.debug(self.res.text)

	self._logger.info("Logged In")
    
    def _get_statement_table(self):

	# View statement history
	
        statement_url = 'https://stmts.chase.com/stmtslist?AI=530767682'
	self.res = self.s.get(statement_url)
	statement_page = BeautifulSoup(self.res.text, 'html.parser')
        
	table = statement_page.find_all('table', id='grid')[0]
	return table

    def scrape(self, account, drive_date):
	
	self._logger.info("Starting scrape for account '%s' ", account)

	table = self._get_statement_table()
	table_body = table.find('tbody')

	rows = table_body.find_all('tr')
	for row in rows:	
	    cols = row.find_all('td')
            link = cols[0].find('a')
	    date_raw = link.text
	    statement_date = datetime.strptime(date_raw, "%B %d, %Y").date()
	
	    self._logger.debug("Statement Date: '%s', Drive Date: '%s' ", statement_date, drive_date)

	    # Break when dates match
	    if statement_date <= drive_date:
		break
	    	
	    # Download statement
	    regex = re.compile("(?<=Close\(')(.*)(?=')", re.MULTILINE)
            statement_url = re.search(regex, link.get('href')).group()	    

	    file = self.s.get(statement_url) 	

	    # Save statement
	    self._save(file, statement_date)

	    row_count += 1
	
	return
	    

    def hasNew(self, account, date):
	
        table = self._get_statement_table()
	table_body = table.find_all('tbody')
	
	# No statement table if new year
        if table_body is None:
            return False

        rows = table_body.find_all('tr')
        cols = rows[0].find_all('td')
        date_raw = cols[0].find('a').text
        latest_date = datetime.strptime(date_raw, "%B %d, %Y").date()

	if latest_date > date:
	    self._logger.info("New statement(s) found")
	    return True
	else:
	    self._logger.info("No new statement(s) found")
	    return False



   
