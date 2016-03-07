from bs4 import BeautifulSoup
import requests
import re
import logging
from datetime import datetime
import os
from scraperbase import ScraperBase


LOGIN_PAGE = 'https://www.prosper.com/borrower/api/v1/user/signin'


class Scraper(ScraperBase):

    def __init__(self, *args, **kwargs):
	super(Scraper, self).__init__(*args, **kwargs)

    def _login(self):

        # Post Login Data
        data = {
        'email' : self.username, 'password' : self.password, 'recaptcha_response' : 'null'}
        self.res = self.s.post(LOGIN_PAGE, data=data)

	self._logger.info("Logged In")
    
    def _get_statement_table(self):

	# View statement history
        statement_url = "https://www.prosper.com/secure/account/common/statements.aspx"
        self.res = self.s.get(statement_url)

        statement_page = BeautifulSoup(self.res.text, 'html.parser')
        table = statement_page.find('table', id='M_MainContent_c7_grid')
        return table

    def scrape(self, account, drive_date):
	
	self._logger.info("Starting scrape for account '%s' ", account)

	table = self._get_statement_table()

	rows = table.find_all('tr')
	iterrows = iter(rows)
	next(iterrows)
	for row in iterrows:	
	    cols = row.find_all('td')
            
            date_raw = cols[0].text.strip()
	    statement_date = datetime.strptime(date_raw, "%m/%d/%Y").date()
	
	    self._logger.debug("Statement Date: '%s', Drive Date: '%s' ", statement_date, drive_date)

	    # Break when dates match
	    if statement_date <= drive_date:
		break
            self._logger.debug(cols)
            self._logger.debug(cols[1])
            statement_url = cols[1].find('a').get('href')

	    file = self.s.get(statement_url) 	

	    # Save statement
	    self._save(file, statement_date)
	
	return
	    

    def hasNew(self, account, date):
	
        table = self._get_statement_table()
    
	rows = table.find_all('tr')
        cols = rows[1].find_all('td')
        
        date_raw = cols[0].text.strip()
        latest_date = datetime.strptime(date_raw, "%m/%d/%Y").date()

	if latest_date > date:
	    self._logger.info("New statement(s) found")
	    return True
	else:
	    self._logger.info("No new statement(s) found")
	    return False



   
