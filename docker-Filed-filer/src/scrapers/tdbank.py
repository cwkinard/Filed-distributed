from bs4 import BeautifulSoup
import requests
import re
import logging
from datetime import datetime
import os
from scraperbase import ScraperBase


LOGIN_PAGE = 'https://onlinebanking.tdbank.com'


class Scraper(ScraperBase):

    def __init__(self, *args, **kwargs):
	super(Scraper, self).__init__(*args, **kwargs)

    def _login(self):

        self.res = self.s.get(LOGIN_PAGE)

        # Pull login page with traceid
        lg_page = BeautifulSoup(self.res.text, 'html.parser').findAll('frame')[0].get('src')

        res = self.s.get(lg_page)
        sub_page = 'https://onlinebanking.tdbank.com/voyLogin.asp?' + lg_page.split('?')[1]

        # Post Login Data
        data = {
        'user' : self.username, 'pin' : self.password}
        self.res = self.s.post(sub_page, data=data)

	# We could either make it to the home page, or hit a security question
        landing_page = BeautifulSoup(self.res.text, 'html.parser')

        # Determine verification and perform, if necessary
        verification = landing_page.find("div", {"id": "td-pagetitlearea"}).find("h1")
        if verification is not None and verification.string == 'Identity Verification':
            question = landing_page.find("td", {"class":"question"}).text.strip().replace(u"\x92", "'")
            self._logger.debug("Hit security question: '%s' ", question)

            # Find the 'Question ID'
            js = landing_page.findAll('script')[13].text
            regex = re.compile('(?<=QuestionID\.value = ")(.*)(?=")', re.MULTILINE)
            question_id = re.search(regex, js).group()

            home_page = 'https://onlinebanking.tdbank.com/ia_fp/ia_challenge.asp?insQuestions=false'
            
	    # Post security question data
            data = {
            'isPostBack' : 'True', 'QuestionAnswer' : self.qa[question], 'QuestionID' : question_id,
            'insQuestions' : '', 'Newanswer' : self.qa[question] }
            self.res = self.s.post(home_page, data=data)

	self._logger.info("Logged In")
    
    def _get_statement_table(self, acctId):

	# View statement history
        statement_url = "https://onlinebanking.tdbank.com/accts/statementsandnotices.asp"
        data = { 'acctId' : acctId, 'pageNav' : 'history' }
        self.res = self.s.post(statement_url, data=data)

        statement_page = BeautifulSoup(self.res.text, 'html.parser')
        table = statement_page.find('table', id='tdResults')
        return table

    def scrape(self, account, drive_date):
	
	self._logger.info("Starting scrape for account '%s' ", account)

	table_body = self._get_statement_table(account['web_id'])

	rows = table_body.find_all('tr')
	iterrows = iter(rows)
	next(iterrows)
	for row in iterrows:	
	    cols = row.find_all('td')
            link = cols[2].find('a').get('href')
	    regex = re.compile('(?<=javascript:getStatement\()(.*)(?=,)', re.MULTILINE)
            date_raw = re.search(regex, link).group()
	    regex = re.compile('(?<=,)(.*)(?=\))', re.MULTILINE)
            index = re.search(regex, link).group()
	    statement_date = datetime.strptime(date_raw, "%Y%m%d").date()
	
	    self._logger.debug("Statement Date: '%s', Drive Date: '%s' ", statement_date, drive_date)

	    # Break when dates match
	    if statement_date <= drive_date:
		break
	    	
	    # Download statement
	    #statement_url = 'https://onlinebanking.tdbank.com/accts/acct_eStatement_View.asp?'
	    #statement_url += ('viewDate=' + date_raw + '&statementIndex=' + index +
		#	      '&acctID=' + account['web_id'])
	    
	    statement_url = 'https://onlinebanking.tdbank.com/accts/Statement.asp'
	    data = { 'refreshTime' : datetime.now().strftime("%Y/%m/%d %I:%M:%S %p"),
		     'viewDate' : date_raw, 'acctID' : account['web_id'],
		     'statementIndex' : index, 'useCache' : 'N' }

	    file = self.s.post(statement_url, data=data) 	

	    # Save statement
	    self._save(file, statement_date)
	
	return
	    

    def hasNew(self, account, date):
	
        table_body = self._get_statement_table(account['web_id'])

	# No statement table if new year
        if table_body is None:
            return False

        rows = table_body.find_all('tr', attrs={'class':'td-table-alt-row'})
        cols = rows[0].find_all('td')
        link = cols[2].find('a').get('href')
        regex = re.compile('(?<=javascript:getStatement\()(.*)(?=,)', re.MULTILINE)
        date_raw = re.search(regex, link).group()
        latest_date = datetime.strptime(date_raw, "%Y%m%d").date()

	if latest_date > date:
	    self._logger.info("New statement(s) found")
	    return True
	else:
	    self._logger.info("No new statement(s) found")
	    return False



   
