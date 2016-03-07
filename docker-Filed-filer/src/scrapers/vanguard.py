from bs4 import BeautifulSoup
import requests
import re
import logging
from datetime import datetime
import os
import urllib
from scraperbase import ScraperBase


LOGIN_PAGE = 'https://investor.vanguard.com/home/'

class Scraper(ScraperBase):

    def __init__(self, *args, **kwargs):
        super(Scraper, self).__init__(*args, **kwargs)

    def _login(self):

        self.res = self.s.get(LOGIN_PAGE)

        home_page = BeautifulSoup(self.res.text, 'html.parser') 
        
        pm_fp = 'version%3D1%26pm%5Ffpua%3Dmozilla%2F5%2E0%20%28windows%20nt%2010%2E0%3B%20wow64%29%20applewebkit%2F537%2E36%20%28khtml%2C%20like%20gecko%29%20chrome%2F47%2E0%2E2526%2E111%20safari%2F537%2E36%7C5%2E0%20%28Windows%20NT%2010%2E0%3B%20WOW64%29%20AppleWebKit%2F537%2E36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F47%2E0%2E2526%2E111%20Safari%2F537%2E36%7CWin32%26pm%5Ffpsc%3D24%7C1706%7C960%7C900%26pm%5Ffpsw%3D%26pm%5Ffptz%3D%2D5%26pm%5Ffpln%3Dlang%3Den%2DUS%7Csyslang%3D%7Cuserlang%3D%26pm%5Ffpjv%3D0%26pm%5Ffpco%3D1'

	login_url = 'https://personal.vanguard.com/us/AuthenticationServiceServlet'

	data = { 
            'USER':self.username, 'PASSWORD':self.password,
            'target':'$SM$/us/MyHome',
            'smauthreason':'0',
            'pm_fp':pm_fp 
        }
        
	self.res = self.s.post(login_url, data=data) 	
        
        landing_page = BeautifulSoup(self.res.text, 'html.parser')
        
        isQuestion = landing_page.find_all('h1', text = re.compile('Answer your security question'), attrs = {'class' : 'option2'})

        if isQuestion:
            table = landing_page.find('table', id='LoginForm:summaryTable')
            rows = table.find_all('tr')
            
            question = rows[1].find_all('td')[1].text
            self._logger.info('Login Question: ' + question)
            
            token = landing_page.find('input', attrs={'name':'ANTI_CSRF_TOKEN', 'type':'hidden'}).get('value')

            data = {
                'cbd_ria':'true', 'AUTHN_AA_ANSWER':self.qa[question], 'AUTHN_AA_BIND_DEVICE':'true',
                'pm_fp':pm_fp, 'smauthreason':'0', 'smagentname':'', 'postpreservationdata':'',
                'target':'$SM$/us/MyHome', 'LoginForm:ANSWER':self.qa[question], 'LoginForm:DEVICE':'true',
                'ANTI_CSRF_TOKEN':token, 'LoginForm':'LoginForm'
            }

            self.res = self.s.post(login_url, data=data)
        
        self._logger.info("Logged In")

    def _set_statement_year(self, year, token):
	
	data = {
	    'cbdCompId':'comp-StmtSummaryForm', 'StmtSummaryForm':'StmtSummaryForm',
	    'StmtSummaryForm:goFilterButton':'StmtSummaryForm:goFilterButton',
	    'cbd_ria':'true', 'StmtSummaryForm:_id1305:state':'', '':str(year),
            'StmtSummaryForm:YearFilterMenu':str(year), '':'All months',
            'StmtSummaryForm:MonthFilterMenu':'ALL', 'StmtSummaryForm:goFilterButton':'StmtSummaryForm:goFilterButton',
            'atoken':'0', 'ANTI_CSRF_TOKEN':token, 'StmtSummaryForm':'StmtSummaryForm'
	}

	year_url = 'https://personal.vanguard.com/us/XHTML/com/vanguard/retail/web/statementsconfirms/view/StmtBase.xhtml'	
	self.res = self.s.post(year_url, data=data)
    
    def _scrape_table(self, table, drive_date):
	
	rows = table.find_all('tr', attrs={'class':['ar', 'wr']})
        rows = (x for x in rows if int(x.get('index')) > 4)
        for row in rows:
            cols = row.find_all('td')
            
            date_raw = cols[0].text
            statement_date = datetime.strptime(date_raw, "%m/%d/%Y").date()

            self._logger.debug("Statement Date: '%s', Drive Date: '%s' ", statement_date, drive_date)

            # Break when dates match
            if statement_date <= drive_date:
                return True

            # Download statement
            statement_url = 'https://personal.vanguard.com'
            statement_url += cols[2].find('a').get('href')

            file = self.s.get(statement_url)
            
	    # Save statement
	    self._save(file, statement_date)

	return False

    def scrape(self, account, drive_date):
	
	self._logger.info("Starting scrape for account '%s' ", account)

        # View statement history
        self.res = self.s.get('https://personal.vanguard.com/us/Statements')
        statement_page =  BeautifulSoup(self.res.text, 'html.parser')

        token = statement_page.find('input', attrs={'name':'ANTI_CSRF_TOKEN', 'type':'hidden'}).get('value')

	# Grab 'year' spans
	years = statement_page.find_all('div',  attrs={'class':'vg-SelOneMenuInput'})[0].find_all('span')
	
	for span in years:
	    year = span.text	
            self._set_statement_year(year, token)
	    
	    statement_html = BeautifulSoup(self.res.text, 'html.parser')

	    table = statement_html.find('table', id='StmtSummaryForm:stmtFilterTable') 

	    if(self._scrape_table(table, drive_date)):
		break 	    
	
	return	    

    def hasNew(self, account, date):
	
        # View statement history
        self.res = self.s.get('https://personal.vanguard.com/us/Statements')
        statement_page =  BeautifulSoup(self.res.text, 'html.parser')

	table = statement_page.find('table', id='StmtSummaryForm:stmtFilterTable')
		
        row = table.find('tr', attrs={'index':'5'})
        date_raw = row.find_all('td')[0].text        
        latest_date = datetime.strptime(date_raw, "%m/%d/%Y").date()
        
	if latest_date > date:
	    self._logger.info("New statement(s) found")
	    return True
	else:
	    self._logger.info("No new statement(s) found")
	    return False



   
