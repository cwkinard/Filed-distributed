import traceback
import logging
import pkgutil
import json
import os
import drive
from scraperbase import ScraperBase
import pika
from oauth2client import tools

def _CreateArgumentParser():
    try:
        import argparse
    except ImportError:
        return None
    parser = argparse.ArgumentParser(description='Filed - Get Organized', parents=[tools.argparser])

    return parser

# argparser is an ArgumentParser that contains command-line options
argparser = _CreateArgumentParser()
flags = argparser.parse_args()


class Filer(object):

    def __init__(self):
	"""        
	Instantiates a new Filer object, which scrapes each website
	defined as a scraper for new documents and files them 
	appropriately in the location defined.

	"""

	self._logger = logging.getLogger('filer')
	self._logger.setLevel(getattr(logging, flags.logging_level))

	self.scrapers = self.load_scrapers()
        self.drive = drive.Drive(flags)
	
	self._logger.info("Initiating Filer")
		

    @classmethod
    def load_scrapers(cls):

        """
        Dynamically loads all the scrapers in the 'scrapers' folder
	that contain 'Scraper' class inheriting from 'ScraperBase'.
        """

        logger = logging.getLogger('filer')

	locations = ['/Filed/src/scrapers']
        logger.info("Loading scrapers from: %s",
                     ', '.join(["'%s'" % location for location in locations]))
        scrapers = []
        for finder, name, ispkg in pkgutil.walk_packages(locations):
            try:
                loader = finder.find_module(name)
                scraper = loader.load_module(name)
            except:
                logger.warning("Skipped scraper '%s' due to an error.", name,
                               exc_info=True)
            else:
                if hasattr(scraper, 'Scraper') and issubclass(scraper.Scraper, ScraperBase):
                    logger.debug("Found scraper '%s'", name)
                    scrapers.append(scraper)
                else:
                    logger.warning("Skipped scraper '%s' because it misses " +
                                   "the 'Scraper' class or it does not inherit " +
				   "the 'ScraperBase' parent class", name)
	logger.info("Scrapers loaded")
        return scrapers
    
    def file(self, msg):
	
	blob = json.loads(msg)
	site = blob.keys()[0]
	    
	self._logger.debug("Scraping '%s'", site)
	# Find appropriate scraper for the account
	scraper = next(x for x in self.scrapers if x.__name__.split('.')[0] == site)	

	# Login Loop (ex. 'bankuser')
	for login in blob[site]:
	    if (login == 'disabled'):
                continue		

	    self._logger.debug("Executing scraper '%s' for login '%s'",
                                scraper.__name__, login)

	    try:
	        # Instantiate scraper for this login (and logs in)
                s = scraper.Scraper(str(login), str(blob[site][login]['password']),
                                    str(blob[site][login]['qa']), flags)
		
    	        # Account Loop (ex. 'checking')
	        for account in blob[site][login]["accounts"]:
		    self._logger.debug("Account '%s' - ", account)
		    date = self.drive.get_latest_from_folder(
				    blob[site][login]["accounts"][account]['drive_id'])
		    self._logger.debug("Last Drive statement date: %s", str(date))

		    # Check if this account has new documents
		    if s.hasNew(blob[site][login]["accounts"][account], date):
		        try:
			    self._logger.debug("New statement(s) found. Downloading...")
			    s.scrape(blob[site][login]["accounts"][account], date)
		        except:
			    self._logger.error('Failed to execute scraper',
                                                   exc_info=True)
		        else:
			    self._logger.debug("Scrape by scraper '%s' completed",
                                       scraper.__name__)
                    	    self._logger.info("Found %d new statements to file", len([name for \
			        name in os.listdir('/Filed/tmp')]))
                    	    
			    # Add files to drive
			    for file in os.listdir('/Filed/tmp'):
			        self.drive.add_file_to_folder(file, os.path.join('/Filed/tmp', 
									         file), 
				        blob[site][login]["accounts"][account]['drive_id'])
			        self._logger.debug("File '%s' saved to Drive", file)
		    	    #delete files from tmp
			    for the_file in os.listdir('/Filed/tmp'):
    			        file_path = os.path.join('/Filed/tmp', the_file)
    			        try:
        			    if os.path.isfile(file_path):
            			        os.unlink(file_path)
				        self._logger.debug("File '%s' deleted from tmp", the_file)
    			        except Exception, e:
        			    self._logger.warning(e)
		    else:
		        self._logger.info("No new statements for '%s' ",
                                   account)
	    except Exception as e:
		self._logger.error("Scraper for '%s' - '%s' failed: %s", site, login, traceback.format_exc())	
        
if __name__ == "__main__":
   
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=format)

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, flags.logging_level))

    # Set pika log level
    pika_logger = logging.getLogger('pika')
    pika_logger.setLevel(logging.ERROR)
 
    filer = Filer()

    credentials = pika.PlainCredentials('filed', 'filed')
    parameters = pika.ConnectionParameters('rabbitmq',
                                           5672,
                                           'filedhost',
                                           credentials)

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare(queue='filer_queue', durable=True)

    def callback(ch, method, properties, body):
	logger.debug('Received: %s', body)
        filer.file(body)
        ch.basic_ack(delivery_tag = method.delivery_tag)

    channel.basic_qos(prefetch_count=1)

    queue = 'filer_queue'
    channel.basic_consume(callback,
                          queue=queue)

    logger.info("Listening to queue '%s'...", queue)
    channel.start_consuming()

    
