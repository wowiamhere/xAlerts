from bottle import route, run, SimpleTemplate, template, Bottle, view

import os
import requests
from bs4 import BeautifulSoup
import hashlib
import re
import time
import tempfile
import uuid

#######################
# NEW
#######################
import unicodedata

# SELENIUM IMPORTS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.chrome.options import Options

tmp_dir = os.path.join( tempfile.gettempdir(), str( uuid.uuid4() ) )
os.makedirs( tmp_dir, exist_ok=True )

sel_ops = Options()
sel_ops.add_argument(f'--user-data-dir={tmp_dir}')
sel_ops.add_argument('--headless')
sel_ops.add_argument('--no-sandbox')
sel_ops.add_argument('--disable-dev-shm-usage')

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
	#r = requests.get('https://extrasalerts.com/la/union/?utm_source=la&utm_medium=button&utm_campaign=site')
	r = requests.get('https://extrasalerts.com/la/casting/?utm_source=extrasalerts&utm_medium=button&utm_campaign=site#browse')

	soup = BeautifulSoup( r.text, 'html.parser' )

	alerts_div = soup.css.select('div.wp-block-group.has-border-color.has-global-padding.is-layout-constrained.wp-block-group-is-layout-constrained');
	
	return alerts_div

# TAKES EACH ALERT AND HASHES TO CHECK IN FUTURE IF THE ALERT HAS CHANGED
def build_hash_arr(cont):
	for alert in alerts:
		alert_text = alert.css.select('p')[1].text
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
	global hshs
	global cur_hshs
	global alerts
	global pass_code
	global tm
	global sel_ops
	global telegram_message

	tm = []

	alerts = get_html()

	#hshs = ['6930da77cbddbf51800bece2f01d7185207fb2ef692df14c899fef3ecc6b146']

	#if( len(hshs) > 0 ):
	if( len( alerts ) > 0 ):
		build_hash_arr( cur_hshs )

		state = [ st in hshs for st in cur_hshs ]		
		#new_alerts = [ alerts[i].css.select('p')[1] for i in range( len(alerts) ) if state[i] == False ]
		new_alerts = [ alerts[i] for i in range( len(alerts) ) if state[i] == False ]		
		if ( len(new_alerts) > 0): 
			driver = webdriver.Chrome( options=sel_ops )
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


					tel_resp = send_telegram_message( telegram_message )
					tm.append( telegram_message )
					telegram_message = ''


				else:
					telegram_message = 3*'--NO PASS!!!--' + '\n' + alert_txt
					tel_resp = send_telegram_message( telegram_message )
					tm.append( telegram_message )
					telegram_message = ''

			driver.quit()

		hshs = cur_hshs
		cur_hshs = []

	else:
		new_alerts = []
		build_hash_arr( hshs )

	return dict(tm = tm) 

if __name__ == '__main__':
	run( app=app, host='localhost', port=8000, debug=True, reloader=True )