import imp
import os
import logging
import pkgutil
import schedule
import time
import sys
import pika
import json
from oauth2client import tools

def _CreateArgumentParser():
    try:
        import argparse
    except ImportError:
        return None
    parser = argparse.ArgumentParser(description='Filed - Get Organized', parents=[tools.argparser])
    parser.add_argument('-s', '--schedule', nargs='?', const='00:00',
                    help="Run Filed as a scheduled service in 24 hour format (ex. '12:01')")
   
    return parser

# argparser is an ArgumentParser that contains command-line options
argparser = _CreateArgumentParser()
flags = argparser.parse_args()

class Filed(object):
    def __init__(self):

        self._logger = logging.getLogger('Filed')
        self._logger.setLevel(getattr(logging, flags.logging_level))

    def run(self):
	# Open Accounts JSON config
	with open('/accounts.json') as data_file:
            accounts = json.load(data_file)


	credentials = pika.PlainCredentials('filed', 'filed')
	parameters = pika.ConnectionParameters('rabbitmq',
                                               5672,
                                               'filedhost',
                                               credentials)

	connection = pika.BlockingConnection(parameters)
	channel = connection.channel()

	channel.queue_declare(queue='filer_queue', durable=True)

	for account in accounts:
	    if (accounts[account]['disabled'] == 'true'):
                    self._logger.info("Site '%s' disabled.", account)
                    continue

            channel.basic_publish(exchange='',
                                  routing_key='filer_queue',
                                  body='{"'+str(account)+'":'+json.dumps(accounts[account])+'}',
                                  properties=pika.BasicProperties(
                                      delivery_mode = 2, # make message persistent
                                  ))
	connection.close()	

if __name__ == "__main__":

    print("\n")
    print("*******************************************************")
    print("*                 FILED - Get Organized               *")
    print("*                   2015 Will Kinard                  *")
    print("*******************************************************")
    print("\n")

    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(format=format)

    logger = logging.getLogger()
    logger.setLevel(getattr(logging, flags.logging_level))

    # Set pika log level
    pika_logger = logging.getLogger('pika')
    pika_logger.setLevel(logging.ERROR)

    try:
        app = Filed()
    except Exception:
        logger.error("Error occured!", exc_info=True)
        sys.exit(1)
    
    if flags.schedule:	
	schedule.every().day.at(flags.schedule).do(app.run)
	logger.info("Scheduled: " + schedule.next_run().strftime("%Y-%m-%d %I:%M %p"))
        while 1:
            schedule.run_pending()
            time.sleep(1)
    else:
        app.run()

