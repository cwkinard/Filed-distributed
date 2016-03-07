from bs4 import BeautifulSoup
import requests
import re
import logging
from datetime import datetime
import os
import urllib
from scraperbase import ScraperBase


LOGIN_PAGE = 'https://www.barclaycardus.com'


class Scraper(ScraperBase):

    def __init__(self, *args, **kwargs):
        super(Scraper, self).__init__(*args, **kwargs)

    def _login(self):

	self.res = self.s.get(LOGIN_PAGE)

	login_page = BeautifulSoup(self.res.text, 'html.parser')

	pm_fp = 'version%3D1%26pm%5Ffpua%3Dmozilla%2F5%2E0%20%28windows%20nt%2010%2E0%3B%20wow64%29%20applewebkit%2F537%2E36%20%28khtml%2C%20like%20gecko%29%20chrome%2F47%2E0%2E2526%2E111%20safari%2F537%2E36%7C5%2E0%20%28Windows%20NT%2010%2E0%3B%20WOW64%29%20AppleWebKit%2F537%2E36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F47%2E0%2E2526%2E111%20Safari%2F537%2E36%7CWin32%26pm%5Ffpsc%3D24%7C1706%7C960%7C900%26pm%5Ffpsw%3D%26pm%5Ffptz%3D%2D5%26pm%5Ffpln%3Dlang%3Den%2DUS%7Csyslang%3D%7Cuserlang%3D%26pm%5Ffpjv%3D0%26pm%5Ffpco%3D1'
        sp = login_page.find('input', attrs={'name':'_sourcePage', 'type':'hidden'}).get('value')
	fp = login_page.find('input', attrs={'name':'__fp', 'type':'hidden'}).get('value')

        # Post Username
        data = { 'username':self.username, 'redirectAction':'', 'login':'Log in', 'INTNAV':
		 'Homepage_CustomerLoginBtn', 'loginButtonAction':'true', 'pm_fp': pm_fp,
		 'redirectAction':'', '_sourcePage':sp, '__fp':fp  }

	login_url = 'https://www.barclaycardus.com/servicing/login'
        self.res = self.s.post(login_url, data=data)

        # Post Password
	pass_page = BeautifulSoup(self.res.text, 'html.parser')
	
	sp = login_page.find('input', attrs={'name':'_sourcePage', 'type':'hidden'}).get('value')
        fp = login_page.find('input', attrs={'name':'__fp', 'type':'hidden'}).get('value')
	
	data = { 'password':self.password, 'submitPassword':'Log in', 'loginButton-button':'Log in',
		 'username':self.username, 'rememberUserName':'false', 'redirectAction':'', 
		 'INTNAV':'Homepage_CustomerLoginBtn', 'loginButtonAction':'true', 'pm_fp': pm_fp,
                 '_sourcePage':sp, '__fp':fp  }

	self.res = self.s.post(login_url, data=data)	
 
	self._logger.info("Logged In")
    
    def _get_statement_dropdown(self):

	statement_url = 'https://www.barclaycardus.com/servicing/activity'
	self.res = self.s.get(statement_url)

	statement_page = BeautifulSoup(self.res.text, 'html.parser')
	statement_url = statement_page.find('nav', id='subNavMenu').findAll('a')[1].get('href')

	self.res = self.s.get('https://www.barclaycardus.com/servicing/' + statement_url)

	# View statement history
        statement_page = BeautifulSoup(self.res.text, 'html.parser')
        dropdown = statement_page.find('select', id='statementsSelect')
        return dropdown

    def scrape(self, account, drive_date):
	
	self._logger.info("Starting scrape for account '%s' ", account)

	dropdown = self._get_statement_dropdown()

	rows = dropdown.find_all('option')
	for row in rows:	
            date_raw = row.text

	    if 'Annual Summary' not in date_raw:
	        statement_date = datetime.strptime(date_raw, "%m/%d/%y").date()
	
	        self._logger.debug("Statement Date: '%s', Drive Date: '%s' ", 
				    statement_date, drive_date)

	        # Break when dates match
	        if statement_date <= drive_date:
		    break
	    
		doc_id = row.get('value')

	        # Download statement
	        statement_url = 'https://www.barclaycardus.com/servicing/mystatements?getStatement=DownloadPDF&documentId=' + str(doc_id)
	    
	        file = self.s.get(statement_url)
	        #self._logger.debug(self.res.text)

		# Save statment
		self._save(file, statement_date)

	return
	    

    def hasNew(self, account, date):

        dropdown = self._get_statement_dropdown()

        rows = dropdown.find_all('option')
	for row in rows:
	    date_raw = rows[0].text

	    if 'Annual Summary' not in date_raw:
                latest_date = datetime.strptime(date_raw, "%m/%d/%y").date()

	        if latest_date > date:
	            self._logger.info("New statement(s) found")
	            return True
	        else:
	            self._logger.info("No new statement(s) found")
	            return False



   
