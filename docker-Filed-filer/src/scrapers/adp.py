from bs4 import BeautifulSoup
import requests
import re
import logging
from datetime import datetime
import os
import urllib
from scraperbase import ScraperBase

LOGIN_PAGE = 'https://agateway.adp.com/siteminderagent/nocert/1452983272/smgetcred.scc?TYPE=16777217&REALM=-SM-iPay%20AG%20User%20[17%3a27%3a52%3a5835]&SMAUTHREASON=0&METHOD=GET&SMAGENTNAME=-SM-GJhM6kK9dRSj%2f%2fJIOxL2bk7urD4vemiZfubVBGrLAGxU0tnw7leGxGsIKs2LWyPV&TARGET=-SM-http%3a%2f%2fipay%2eadp%2ecom%2fiPay%2fprivate%2findex%2ejsf'


class Scraper(ScraperBase):

    def __init__(self, username, password, qa, flags):
	ScraperBase.__init__(self, urllib.quote(username), urllib.quote(password), qa, flags)

    def _login(self):

	url_split = LOGIN_PAGE.split('https://')
	l_page = 'https://' + self.username + ':' + self.password + '@' + url_split[1]

	# Submit creds via basic auth
        self.res = self.s.get(l_page)

	# Redirect to index
	self.res = self.s.get('https://ipay.adp.com/iPay/index.jsf')

	# Submit hidden form
	login_url = 'https://ipay.adp.com/iPay/login.jsf'
	data = { 'normalLogin':'yes' }
	self.res = self.s.post(login_url, data=data) 	

	# Redirect to private index
        self.res = self.s.get('https://ipay.adp.com/iPay/private/index.jsf')
	
	# Go to first year
	statement_html = self._get_statement_html()
	viewState = statement_html.find('input', attrs={'name':'javax.faces.ViewState', 'type':'hidden'}).get('value')
	data = {
            'statement':'statement',
            'statement':'changeStatementsType:1',
            'javax.faces.ViewState':viewState,
            'statement:year1':'statement:year1'
        }

        year_url = 'https://ipay.adp.com/iPay/private/listDoc.jsf'
        self.res = self.s.post(year_url, data=data)
	
	self._logger.info("Logged In")

    def _set_statement_year(self, year, viewState):
	
	data = {
	    'statement':'statement',
	    'statement:changeYear':'year'+str(year),
	    'javax.faces.ViewState':viewState
	}

	year_url = 'https://ipay.adp.com/iPay/private/listDoc.jsf'	
	self.res = self.s.post(year_url, data=data)
    
    def _get_statement_html(self):
       
	# View statement history
        statement_url = BeautifulSoup(self.res.text, 'html.parser').findAll('frame')[0].get('src')
        self.res = self.s.get('https://ipay.adp.com' + statement_url)
        statement_html =  BeautifulSoup(self.res.text, 'html.parser')

	return statement_html

    def _scrape_table(self, table_body, drive_date, viewState):
	
	rows = table_body.find_all('tr')
        row_count = 0
        for row in rows:
            cols = row.find_all('td')
            date_raw = cols[0].find('a').text
            statement_date = datetime.strptime(date_raw, "%m/%d/%Y").date()

            self._logger.debug("Statement Date: '%s', Drive Date: '%s' ", statement_date, drive_date)

            # Break when dates match
            if statement_date <= drive_date:
                return True

            # Download statement
            proxy_url = 'https://ipay.adp.com/iPay/private/listDoc.jsf'
            data = { 'statement':'statement', 'statement:changeStatementsType':'1',
                     'javax.faces.ViewState':viewState,
                     'statement:checks:'+str(row_count)+':view':'statement:checks:'+str(row_count)+':view' }

            self.res = self.s.post(proxy_url, data=data)
            statement_url = BeautifulSoup(self.res.text, 'html.parser').findAll('iframe')[0].get('src')

            file = self.s.get('https://ipay.adp.com' + statement_url)

	    # Save statement
	    self._save(file, statement_date)

            row_count += 1

	return False

    def scrape(self, account, drive_date):
	
	self._logger.info("Starting scrape for account '%s' ", account)

	statement_html = BeautifulSoup(self.res.text, 'html.parser')

	viewState = statement_html.find('input', attrs={'name':'javax.faces.ViewState', 'type':'hidden'}).get('value')

	# Grab 'year' columns
	years = statement_html.find('table', id='statement:changeYear').find('tr').find_all('td')
	
	for col in years:
	    year = col.find('input').get('value').split('r')[1]	
	    if(col.find('input').get('checked') is None):
		self._set_statement_year(year, viewState)
	    
	    statement_html = BeautifulSoup(self.res.text, 'html.parser')

	    table = statement_html.find('table', id='statement:checks')
	    table_body = table.find_all('tbody')[1]

	    if(self._scrape_table(table_body, drive_date, viewState)):
		break 	    
	
	return	    

    def hasNew(self, account, date):
	
        statement_html = BeautifulSoup(self.res.text, 'html.parser')
	table = statement_html.find('table', id='statement:checks')
	table_body = table.find_all('tbody')[1]	
	
        rows = table_body.find_all('tr')
        cols = rows[0].find_all('td')
        date_raw = cols[0].find('a').text
        latest_date = datetime.strptime(date_raw, "%m/%d/%Y").date()

	if latest_date > date:
	    self._logger.info("New statement(s) found")
	    return True
	else:
	    self._logger.info("No new statement(s) found")
	    return False



   
