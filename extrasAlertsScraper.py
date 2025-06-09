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
bot_token = '7756998109:AAGHjhJiL48bpUv0fqVEpveoV_58nMi8Kdw'
chat_id = '6451638522'
telegram_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
telegram_message = ''


hshs = []
cur_hshs = []
alerts = None
pass_code = None


def get_html():
	r = requests.get('https://extrasalerts.com/la/casting/union')

	soup = BeautifulSoup( r.text, 'html.parser' )

	alerts_div = soup.css.select('div.wp-block-group > div.wp-block-group > div.wp-block-group')[0]
	alerts_div = alerts_div.css.select('div', recursive=False )[0]
	
	return alerts_div.css.select('div.wp-block-group > div.wp-block-group ')

def build_hash_arr(cont):
	for alert in alerts:
		alert_text = alert.css.select('p')[1].text
		cont.append( hashlib.sha256( alert_text.encode('utf-8') ).hexdigest() )

def to_file():
	with open('test1.html', 'w') as f:
		for alert in alerts:
			f.write( str( alert ) )

def send_telegram_message(msg):
	payload = { 'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML' }
	return requests.post( telegram_url, data=payload )



while(True):
	alerts = get_html()
	to_file()

	hshs = ['e066746fa56a80cc2c9b311d936296bada06dc36ad175be1179194e657925e7', 'fd074d6ce8b3bd5d6ef4e1cdb6da5fc08fcb455eb3000686f0a864cac81c349', '5879a23401aac1fc05c39fec69a1f96521930aefcf07ebad7c9aaa93d32073d8', '105c2cddc94b5a792a2dd9f5618aa1116a50e7318887559e65d9ada5c66b9921', '6a5fb63332e69064e71e14b045cc31755f9ef1c839438d546f1a0a0f5e1d083a', '1455663924510b52ded63ce5dd9b6cbbd0acc8756c18058e1321771a4078c0e7', 'fd24d248fbf449561fda8478b2f792f13304d3497b96ada080afb6bae38e5822', 'c2997ed170b8c5a55f16626b583d4568edc67248f2b327d5d6941883d2c3c964', 'ef5793bfcd8e0bc5e768fc4a03227ce430bc1765ccb7b8833fea736b1f73994f', '8a8d13321ccacea2b95cd8af0b7b6115b2f376247c049c00037c5a9d3051ef8a', '39ed9f23a1e57fcd58c68b9629bdb34ef6a43b4c1eb813e8ba9190580bb973c1', 'c76dd47e79909907aa61e9d24d14314cb136f9dcdcba3c9dc8bf6af2f545616f']


	if( len(hshs) > 0 ):
		build_hash_arr( cur_hshs )
		print('current!!!!--> ', cur_hshs)

		state = [ st in hshs for st in cur_hshs ]
		new_alerts = [ alerts[i].css.select('p')[1] for i in range( len(alerts) ) if state[i] == False ]
		print('NEW!!!!!--->', new_alerts )
		
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

					#driver.quit()

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
					telegram_message = ''

				else:
					telegram_message = 3*'--NO PASS!!!--' + '\n' + alert_txt
					tel_resp = send_telegram_message( telegram_message )
					telegram_message = ''

			driver.close()

		hshs = cur_hshs
		cur_hshs = []
		breakpoint()

	else:
		build_hash_arr( hshs )

	time.sleep(30)


