from bs4 import BeautifulSoup
import requests
import re
import logging
from datetime import datetime
import os
import calendar
from scraperbase import ScraperBase


LOGIN_PAGE = 'https://mybenefitwallet.com/hsa/auth/verifyuser'


class Scraper(ScraperBase):

    def __init__(self, *args, **kwargs):
        super(Scraper, self).__init__(*args, **kwargs)

    def _login(self):

        # Post Login Data
        data = { 'username' : self.username, 'bankIdentifier' : 'Mellon' }
        self.res = self.s.post(LOGIN_PAGE, data=data)
	
	pass_page = 'https://mybenefitwallet.com/hsa/j_spring_security_check'

	data = { 'j_username' : self.username, 'bankIdentifier' : 'Mellon', 'trustPC' : 'true', 'sendPass' : 'N', 'j_password' : self.password } 
	self.res = self.s.post(pass_page, data=data)	

	# Perform SAML auth
	saml_page = 'https://member.mybenefitwallet.com/benefitwalletsaml/'
	pass_page = BeautifulSoup(self.res.text, 'html.parser')
	saml_rsp = pass_page.find('input', attrs={'name':'SAMLResponse', 'type':'hidden'}).get('value')

	data = { 'TARGET' : '', 'SAMLResponse' : saml_rsp }
	self.res = self.s.post(saml_page, data=data)

	self._logger.info("Logged In")
    
    def _get_statement_dropdown(self):

	# View statement history
        statement_url = 'https://member.mybenefitwallet.com/portal/CC/cdhportal/cdhaccount/mellonstatements'
        self.res = self.s.get(statement_url)
	#self._logger.debug(self.res.text)
        statement_page = BeautifulSoup(self.res.text, 'html.parser')
        dropdown = statement_page.find('select', id='statementMonthYear')
        return dropdown

    def scrape(self, account, drive_date):
	
	self._logger.info("Starting scrape for account '%s' ", account)

	dropdown = self._get_statement_dropdown()

	rows = dropdown.find_all('option')
	for row in rows:	
            date_raw = row.get('value')
	    statement_date = datetime.strptime(date_raw, "%m/%Y").date()
	    day = calendar.monthrange(statement_date.year, statement_date.month)[1]
	    statement_date.replace(day=day)
	
	    self._logger.debug("Statement Date: '%s', Drive Date: '%s' ", statement_date, drive_date)

	    # Break when dates match
	    if statement_date <= drive_date:
		break
	    
	    statement_page = BeautifulSoup(self.res.text, 'html.parser')
	    flowkey = statement_page.find('input', attrs={'name':'_flowExecutionKey', 'type':'hidden'}).get('value')
	
	    # Download statement
	    statement_url = 'https://member.mybenefitwallet.com/portal/CC/portal/account/benefitWalletSso?RelayState=ESTATEMENT&month=' + str(statement_date.month) + '&year=' + str(statement_date.year) + '2015'
	    
	    #data = { '_flowExecutionKey' : flowkey,
		     #'statementMonthYear' : date_raw }

	    #file = self.s.post(statement_url, data=data) 	
	    self.res = self.s.get(statement_url)
	    #self._logger.debug(self.res.text)

	    
            # Perform SAML auth
            saml_page = 'https://gateway.hsamember.com/SingleSignOnWeb/Saml2Gateway?clientid=CYC'
            sso_page = BeautifulSoup(self.res.text, 'html.parser')
            saml_rsp = sso_page.find('input', attrs={'name':'SAMLResponse', 'type':'hidden'}).get('value')

            data = { 'SAMLResponse' : saml_rsp }
            self.res = self.s.post(saml_page, data=data)

	    token_page = 'https://mybenefitwallet.com/hsa/SSOTokenLoginControllerForSAML/SSOTokenLogin'
            sso_page = BeautifulSoup(self.res.text, 'html.parser')
            month = sso_page.find('input', attrs={'name':'month', 'type':'hidden'}).get('value')
	    relayState = sso_page.find('input', attrs={'name':'relayState', 'type':'hidden'}).get('value')
	    userType = sso_page.find('input', attrs={'name':'userType', 'type':'hidden'}).get('value')
	    bankIdentifier = sso_page.find('input', attrs={'name':'bankIdentifier', 'type':'hidden'}).get('value')
	    userId = sso_page.find('input', attrs={'name':'userId', 'type':'hidden'}).get('value')
	    accountNumber = sso_page.find('input', attrs={'name':'accountNumber', 'type':'hidden'}).get('value')
	    samlType = sso_page.find('input', attrs={'name':'samlType', 'type':'hidden'}).get('value')
	    token = sso_page.find('input', attrs={'name':'token', 'type':'hidden'}).get('value')
	    company = sso_page.find('input', attrs={'name':'company', 'type':'hidden'}).get('value')	
	    year = sso_page.find('input', attrs={'name':'year', 'type':'hidden'}).get('value')

            data = { 'month':month, 'relayState':relayState, 'userType':userType, 'bankIdentifier':bankIdentifier, 'userId':userId, 'accountNumber':accountNumber, 'samlType':samlType, 'token':token, 'adminId':'', 'company':company, 'year':'nqZ5f0jJSbLP1F9JRC9l+g==', 'applicationEntryPoint':'' }

	    headers = { 'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Encoding':'gzip, deflate', 'Content-Type':'application/x-www-form-urlencoded', 'Host':'mybenefitwallet.com', 'Origin':'https://gateway.hsamember.com', 'Referer':'https://gateway.hsamember.com/SingleSignOnWeb/Saml2Gateway?clientid=CYC', 'Upgrade-Insecure-Requests':'1', 'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36' }

            file = self.s.post(token_page, data=data, headers=headers)

	    # Save statement
	    self._save(file, statement_date)
	
	return
	    

    def hasNew(self, account, date):

        dropdown = self._get_statement_dropdown()

        rows = dropdown.find_all('option')
	date_raw = rows[0].get('value')
        latest_date = datetime.strptime(date_raw, "%m/%Y").date()
        day = calendar.monthrange(latest_date.year, latest_date.month)[1]
        latest_date.replace(day=day)	

	if latest_date > date:
	    self._logger.info("New statement(s) found")
	    return True
	else:
	    self._logger.info("No new statement(s) found")
	    return False



   
