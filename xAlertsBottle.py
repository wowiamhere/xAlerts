from bottle import route, run, SimpleTemplate, template, Bottle, view

import os
import requests
from bs4 import BeautifulSoup
import hashlib
import re
import time
import tempfile
import uuid
import shutil
from threading import Lock
import unicodedata
import atexit

# SELENIUM IMPORTS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# FOR LOGGING
import logging

logging.basicConfig(
	filename='/var/log/xAlerts.log',
	level=logging.DEBUG,
	format='%(process)d %(processName)s %(thread)d %(threadName)s %(asctime)s [%(levelname)s] %(message)s \n'
)
logging.info('xAlerts started.')


# FOR TEMP DIRECTORY FOR DRIVER(CHROME)
#tmp_dir = os.path.join( tempfile.gettempdir(), str( uuid.uuid4() ) )
#os.makedirs( tmp_dir, exist_ok=True )

'''
def clean_tmp():
	try:
		shutil.rmtree( tmp_dir )
		logging.info( 'tmp removed' )
	except Exception as e:
		logging.exception(r'Error removing tmp: -> {e}')

atexit.register( clean_tmp )
'''

sel_ops = Options()
#sel_ops.add_argument(f'--user-data-dir={tmp_dir}')
sel_ops.add_argument('--headless')
sel_ops.add_argument('--no-sandbox')
sel_ops.add_argument('--disable-dev-shm-usage')
sel_ops.add_argument('--disable-gpu')
sel_ops.add_argument('--disable-software-rasterizer')
#sel_ops.add_argument('--remote-debugging-port=9222')
#sel_ops.add_argument('--single-process')
#sel_ops.add_argument('--no-zygote')

sel_ops.add_argument('--user-data-dir=/tmp/xAlerts/chrome-profile')
sel_ops.add_argument('--profile-directory=Default')

sel_ops.add_argument('--disk-cache-size=0')
sel_ops.add_argument('--media-cache-size=0')
sel_ops.add_argument('--disable-application-cache')
sel_ops.add_argument('--disable-gpu-shader-disk-cache')
sel_ops.add_argument('--disable-ipv6')
sel_ops.add_argument('--host-resolver-rules=MAP localhost 127.0.0.1')
sel_ops.add_argument('--disable-background-networking')
sel_ops.add_argument('--disable-background-time-throttling')
sel_ops.add_argument('--disable-backgrounding-occluded-windows')
sel_ops.add_argument('--disable-renderer-backgrounding')
sel_ops.add_argument('--no-first-run')
sel_ops.add_argument('--no-default-browser-check')
sel_ops.add_argument('--disable-default-apps')
sel_ops.add_argument('--disable-extensions')
sel_ops.add_argument('--mute-audio')

# for selenium
service = Service('/usr/local/bin/chromedriver')

driver = None
driver_lock = Lock()

def get_driver():
	global driver 
	global service
	with driver_lock:
		if driver is None:
			logging.info('...........Getting Driver.')
			driver = webdriver.Chrome( service=service, options=sel_ops )
	logging.info('Driver loaded')
	return driver

def quit_driver():
    global driver
    if driver is not None:
        try:
            driver.quit()
            logging.info('Driver QUIT.')
        except Exception as e:
        	logging.exception(f'Driver quit ERROR:-> {e}')
        driver = None

atexit.register(quit_driver)	

def reset_driver():
	global driver
	if driver:
		try:
			driver.delete_all_cookies()
			driver.execute_script('window.localStorage.clear();')
			driver.execute_script('window.sessionStorage.clear();')
			logging.info('Driver RESET')
		except Exception as e:
			logging.exception(f'Driver reset ERROR:-> {e}')
			



# FOR TELEGRAM
bot_token = os.environ.get('telXBotToken')
chat_id = '6451638522'
telegram_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
telegram_message = ''
tm = []

# FOR KEEPING TRACK OF NEW ALERTS
hshs = []
cur_hshs = []
alerts = None
pass_code = None

# GETS A NEW ALERTS PAGE AND RETRIEVES AND POPULATES THE ALERT VARIABLE
def get_html():
	r = requests.get('https://extrasalerts.com/la/casting/')

	soup = BeautifulSoup( r.text, 'html.parser' )

	alerts_div = soup.css.select('div.wp-block-group.has-border-color.has-global-padding.is-layout-constrained.wp-block-group-is-layout-constrained');

	union_alerts = []
	
	for a in alerts_div:
		txt = unicodedata.normalize( 'NFKD', a.text )
		union = re.search(r'(?<!non)union', txt )
		if( union != None):
			union_alerts.append( a )

	logging.info('union_alerts fetched (get_html())')

	return union_alerts

# TAKES EACH ALERT AND HASHES TO CHECK IN FUTURE IF THE ALERT HAS CHANGED
def build_hash_arr(cont):
	for alert in alerts:
		alert_text = unicodedata.normalize( 'NFKD', alert.text )
		cont.append( hashlib.sha256( alert_text.encode('utf-8') ).hexdigest() )


# ONCE A NEW ALERT IS DETECTED IT SENDS IT TO TELEGRAM AS AN ALERT TO USER
def send_telegram_message(msg):
	payload = { 'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML' }
	return requests.post( telegram_url, data=payload )


# THE HTTP APPLICATION
app = Bottle()

# ROUTE FOR PINGING EVERY 15-30 SECONDS THROUGH A CRON JOB (POTENTIALLY) AND CHECKING FOR NEW ALERTS
@app.route('/new')
@view('new_alerts')
def new_alerts():
	
	logging.info('/new route requested')

	global hshs
	global cur_hshs
	global alerts
	global pass_code
	global tm
	global sel_ops
	global telegram_message
	global driver

	tm = []

	if driver is None:
		driver = get_driver()

	alerts = get_html()
	reset_driver()

	if( len( alerts ) > 0 ):

		build_hash_arr( cur_hshs )

		state = [ st in hshs for st in cur_hshs ]		
		new_alerts = [ alerts[i] for i in range( len(alerts) ) if state[i] == False ]

		if ( len(new_alerts) > 0): 
			for alert in new_alerts:

				alert_txt = unicodedata.normalize( 'NFKD', alert.text )
				alert_pass = re.search(r'PASSWORD:.*\d\d\d\d', alert_txt )

				if( alert_pass != None):
					alert_pass = re.search(r'\d\d\d\d', alert_pass.group() ).group()
					alert_url = alert.a.attrs['href']
					
					driver.get( alert_url )

					pass_input = driver.find_elements(By.TAG_NAME, 'input')
					pass_input[1].send_keys( alert_pass )
					pass_input[2].click()

					logging.info('DRIVER WAITS 2 SECONDS FOR ELEMENT .entry-content > p')
					WebDriverWait( driver, 2 ).until( EC.presence_of_element_located( (By.CSS_SELECTOR, '.entry-content > p') ) )
					
					a_elements = driver.find_elements(By.TAG_NAME, 'a')
					p_elements = driver.find_elements(By.CSS_SELECTOR, '.entry-content > p')


					for p in p_elements:

						a = p.find_elements( By.TAG_NAME, 'a')

						if( len( a ) == 0 ):
							telegram_message += p.text + '\n'
						else:
							telegram_message += '\n'
							for link in a:
								telegram_message += link.get_attribute( 'outerHTML') + '\n\n'


					logging.info('Sending Telegram Message')

					tel_resp = send_telegram_message( telegram_message )
					tm.append( telegram_message )
					telegram_message = ''


				else:
					logging.info('Sending Telegram Message (NO PASS)')

					telegram_message = 3*'--NO PASS!!!--' + '\n' + alert_txt
					tel_resp = send_telegram_message( telegram_message )
					tm.append( telegram_message )
					telegram_message = ''


		logging.info('New alert Telegram message send and ready to display under /new.')
		hshs = cur_hshs
		cur_hshs = []

	else:
		logging.info('No new alerts found')
		new_alerts = []
		build_hash_arr( hshs )

	return dict(tm = tm) 

if __name__ == '__main__':
	run( app=app, host='0.0.0.0', port=8000, debug=True, reloader=False )
