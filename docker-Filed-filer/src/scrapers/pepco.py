import logging
from datetime import datetime
import os
import re
import time
import requests
from bs4 import BeautifulSoup
from random import randint
from scraperbase import ScraperBase

LOGIN_PAGE = 'https://webapps2.pepco.com/login/pepco/'


class Scraper(ScraperBase):

    def __init__(self, *args, **kwargs):
        super(Scraper, self).__init__(*args, **kwargs)

    def _login(self):

        # Post Username
	data = { 'userid' : self.username }
        self.res = self.s.post(LOGIN_PAGE, data=data)

	# Request Dashboard
	self.res = self.s.get('https://webapps2.pepco.com/dashboard/pepco/')

	# Post Password
	login_url = 'https://webapps.pepcoholdings.com/auth/loginIDM.html'
	data = { 'UserId' : self.username, 'Password' : self.password }
	self.res = self.s.post(login_url, data=data)

	proxy_page = BeautifulSoup(self.res.text, 'html.parser')

	# Request Dashboard
	viewState = proxy_page.find('input', attrs={'id':'__VIEWSTATE', 'type':'hidden'}).get('value')
	viewStateGen = proxy_page.find('input', attrs={'id':'__VIEWSTATEGENERATOR', 'type':'hidden'}).get('value')
	event = proxy_page.find('input', attrs={'id':'__EVENTVALIDATION', 'type':'hidden'}).get('value')	

	login_url = 'https://webapps2.pepco.com/dashboard/pepco/'
	data = { '__EVENTTARGET' : '', '__EVENTARGUMENT' : '', '__VIEWSTATE' : viewState, '__VIEWSTATEGENERATOR' : viewStateGen, '__EVENTVALIDATION' : event, 'ctl01$ctnMainContent$btnLoad' : '' }
	self.res = self.s.post(login_url, data=data)

	proxy_page = BeautifulSoup(self.res.text, 'html.parser')

	# Request Landing
	viewState = proxy_page.find('input', attrs={'id':'__VIEWSTATE', 'type':'hidden'}).get('value')
        viewStateGen = proxy_page.find('input', attrs={'id':'__VIEWSTATEGENERATOR', 'type':'hidden'}).get('value')
        event = proxy_page.find('input', attrs={'id':'__EVENTVALIDATION', 'type':'hidden'}).get('value')

        landing_url = 'https://webapps2.pepco.com/dashboard/pepco/landing.aspx'
        data = { '__EVENTTARGET' : '', '__EVENTARGUMENT' : '', '__VIEWSTATE' : viewState, '__VIEWSTATEGENERATOR' : viewStateGen,
		 '__EVENTVALIDATION' : event, 'ctl01$ctnMainContent$btnLoad' : '', 'ctl01$ctnMainContent$ScriptManager1' : 'ctl01$ctnMainContent$UpdatePanel1|ctl01$ctnMainContent$btnLoad',
		 '__ASYNCPOST' : 'true' }
        #self.res = self.s.post(landing_url, data=data)

	self._logger.info("Logged In")

    def _get_statement_table(self):
	
	# View statement page 
	self.res = self.s.get('https://webapps2.pepco.com/dashboard/pepco/ebill.aspx')
	self.res = self.s.get('https://webapps2.pepco.com/ebill/pepco/3535303135303432333232/viewebill.ashx')

	# View statement history
	rand3 = randint(100,999)
        statement_url = 'https://webapps2.pepco.com/ebill/pepco/phiweb/consumer/documents/menu.action?clearsessionhelper=true&dojo.preventCache='
	statement_url += str(int(time.time())) + str(rand3)

        self.res = self.s.get(statement_url)

        statement_page = BeautifulSoup(self.res.text, 'html.parser')
        table = statement_page.find('table', id='allstatementextendedlist_item')

        return table

    def scrape(self, account, drive_date):
	
	self._logger.info("Starting scrape for account '%s' ", account)

	table = self._get_statement_table()
	table_body = table.find('tbody')

	rows = table_body.find_all('tr', attrs={'class': re.compile(r'app_list_row')})
	for row in rows:
	    cols = row.find_all('td')
	    acctno = cols[1].text
	    statement_date = datetime.strptime(cols[3].text, "%m/%d/%Y").date()

	    link = cols[0].find('a').get('href')
            regex = re.compile('(?<=statementid=)(.*)(?=&)', re.MULTILINE)
	    statementid = re.search(regex, link).group()

	    self._logger.debug("Statement Date: '%s', Drive Date: '%s' ", statement_date, drive_date)

	    # Break when dates match
            if statement_date <= drive_date:
                break

            # Download statement
	    statement_url = 'https://webapps2.pepco.com/ebill/pepco/phiweb/consumer/documents/renderDocument.action?'
	    statement_url += ('accountno=' + acctno + '&statementid=' + statementid)

	    file = self.s.get(statement_url)

	    # Save File to tmp
	    self._save(file, statement_date)
	
	return

    def hasNew(self, account, date):
	table = self._get_statement_table()
        table_body = table.find('tbody')

        rows = table_body.find_all('tr')
	col = rows[0].find_all('td')
	latest_date = datetime.strptime(col[3].text, "%m/%d/%Y").date()

	if latest_date > date:
            self._logger.info("hasNew(): New statement found.")
	    return True
        else:
	    self._logger.info("hasNew(): No new statements found.")
            return False





	



