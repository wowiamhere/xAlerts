from bottle import route, run, SimpleTemplate, template, Bottle, view

import os
import requests
from bs4 import BeautifulSoup
import hashlib
import re
import time

# SELENIUM IMPORTS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 

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
	r = requests.get('https://extrasalerts.com/la/casting/union')

	soup = BeautifulSoup( r.text, 'html.parser' )

	alerts_div = soup.css.select('div.wp-block-group > div.wp-block-group > div.wp-block-group')[0]
	alerts_div = alerts_div.css.select('div', recursive=False )[0]
	
	return alerts_div.css.select('div.wp-block-group > div.wp-block-group ')


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

	tm = []

	alerts = get_html()

	hshs = ['6930da77cbddbf51800bece2f01d7185207fb2ef692df14c899fef3ecc6b146', 'a18cf7fee1202e0e3a537faa5ec8ff9541b3d2add9dd3e16dbc7ae3a7d974d4', 'e5ab718b3aa6d6af0d8e1d5bd36a6347252b8eac4bf65b7ffe124d7431e226e6', 'bd527dd572db5c3a367f9258bf7aabc18918183382df0a6b86b68f46a898360e', '0ce33391508eb921599a37962b36c897a0b0d52094d5e65da88cc42e9210c9c6', '02f208d7ea69d8435e497857b724863993d4ba820def154fdb8ba98638b6ee06', 'c94ef83ec605e94dd158f11fecc1b861068d1d176ba32eb8258ff883f070af94', '838b82c680c96a9bb719a9c9f43e653bc447be6f196a2ed51a23bd164b435e48', 'bbfc174eadee19c8b5aa1651c261c023d252b3e6a036e2da545c30c2c646375c', 'f428f7e689be7c27fde1eba49b354f1787b61efe0440c23e3e266c52d6a83909', '14a6e6010ca6171f572b7bc939f319ad9a535e5ff89365a025e30f4b8144263f', 'a1ad9d5e6ea15a8cf2624f90757e455d79cf42c3e8d03479d848cae81e59fc4f']

	if( len(hshs) > 0 ):
		build_hash_arr( cur_hshs )

		state = [ st in hshs for st in cur_hshs ]
		new_alerts = [ alerts[i].css.select('p')[1] for i in range( len(alerts) ) if state[i] == False ]
		
		if ( len(new_alerts) > 0): 
			driver = webdriver.Chrome()
			
			for alert in new_alerts:

				alert_txt = alert.text
				alert_pass = re.search('PASS:.*\d\d\d\d', alert_txt )

				if( alert_pass != None):
					alert_pass = re.search('\d\d\d\d', alert_pass.group() ).group()
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
							pass
						else:
							telegram_message += '\n'
							for link in a:
								telegram_message += link.get_attribute( 'outerHTML') + '\n\n'
								pass


					tel_resp = send_telegram_message( telegram_message )
					tm.append( telegram_message )
					telegram_message = ''

				else:
					telegram_message = 3*'--NO PASS!!!--' + '\n' + alert_txt
					tel_resp = send_telegram_message( telegram_message )
					tm.append( telegram_message )
					telegram_message = ''

			driver.close()

		hshs = cur_hshs
		cur_hshs = []

	else:
		new_alerts = []
		build_hash_arr( hshs )

	return dict(tm = tm) 


app.run( host='localhost', port=8080 )