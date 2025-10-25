
from bottle import route, run, SimpleTemplate, template, Bottle, view, redirect, request
from bs4 import BeautifulSoup
from threading import Lock
from urllib.parse import urlparse, parse_qs, urlencode

import os, time, hashlib, re, tempfile, uuid, shutil, threading, unicodedata, atexit, logging, requests_html


logging.basicConfig(
    filename='/var/log/xAlerts.log',
    level=logging.DEBUG,
    format='%(process)d %(processName)s %(thread)d %(threadName)s %(asctime)s [%(levelname)s] %(message)s \n'
)
logging.info('xAlerts started.')

# FOR TELEGRAM
bot_token = os.environ.get('telXBotToken')
chat_id = '6451638522'
telegram_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
telegram_message = ''
for_view = dict()

# FOR KEEPING TRACK OF NEW ALERTS
hshs = []
cur_hshs = []
alerts = None
pass_code = None

# FOR REQUESTS
session = requests_html.HTMLSession()

# GETS A NEW ALERTS PAGE AND RETRIEVES AND POPULATES THE ALERT VARIABLE
def get_html():
    global session
    r = session.get('https://extrasalerts.com/la/casting/')

    alerts_div = r.html.find('div.wp-block-group.has-border-color.has-global-padding.is-layout-constrained.wp-block-group-is-layout-constrained');

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
    global session, telegram_url
    payload = { 'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML' }
    return session.post( telegram_url, data=payload )


last_run = 0
CHECK_INTERVAL = 30  # seconds

# lock to prevent concurrent background runs
check_lock = threading.Lock()

def check_for_new_alerts():
    global hshs, cur_hshs, alerts, tm, telegram_message, session, for_view

    for_view.clear()
    for_view['new'] = ''
    for_view['no_pass'] = ''
    with check_lock:
        logging.info('Background check_for_new_alerts() started')
        try:
            alerts = get_html()

            if len(alerts) == 0:
                logging.info('No alerts fetched')
                return

            build_hash_arr(cur_hshs)
            state = [st in hshs for st in cur_hshs]
            new_alerts = [alerts[i] for i in range(len(alerts)) if not state[i]]

            if len(new_alerts) == 0:
                logging.info('No NEW alerts detected')
                hshs = cur_hshs
                return

            for alert in new_alerts:


                alert_txt = unicodedata.normalize('NFKD', alert.text)
                alert_pass = re.search(r'PASSWORD:.*\d\d\d\d', alert_txt)

                if alert_pass:

                    alert_pass = re.search(r'\d\d\d\d', alert_pass.group()).group()

                        # comes in the form https://ip.com/la/casting/23434?askdfdk
                    alert_url = list( alert.links )[0].split('?')[0]
                    data_for_post = dict( redirect_to=alert_url, post_password=alert_pass, Submit='Enter')
                    url_for_access = 'https://2025.extrasalerts.com/wp-pass.php'
                    r = session.post( url_for_access , data=data_for_post )
                    r = session.get( alert_url )

                    elements = r.html.find('.entry-content > p')

                    for el in elements:
                        for_view['new'] += el.html
                        if not el.find('a'):
                            telegram_message += el.text + '\n\n'
                        else:
                            for l in el.find('a'):
                                l_href  = l.attrs['href']
                                if ( l_href.find('mailto') == 0):
                                    l_parse = urlparse( l_href )
                                    l_to = l_parse.path
                                    l_subject = parse_qs( l_parse.query )['subject'][0]
                                    l_subject = l_subject[ l_subject.find('RE:')+3:].strip()
                                    l_url_base = 'http://64.181.234.48:8000/email'
                                    l_url_params = urlencode( { 'to': l_to, 'subject': l_subject } )
                                    l_url = f'{l_url_base}?{l_url_params}'
                                    telegram_message += f'<a href="{l_url}">SUBMIT</a>'
                                else:
                                    telegram_message += l.html + '\n\n'


                    r = send_telegram_message(telegram_message)
                    logging.info('Telegram message sent for new alert.')
                    telegram_message = ''

                else:
                    telegram_message += '\n--- NO PASSWORD ---\n'
                    telegram_message += alert.text + '\n'

                    if alert.links:
                        for l in alert.find('a'):
                            telegram_message += '\n\n' + l.html + '\n'
            
                    telegram_message += '-' * 30
                    for_view['no_pass'] += alert.html

            if telegram_message:
                send_telegram_message(telegram_message)
                telegram_message = ''
                logging.info('Telegram message for old alert.')

            hshs = cur_hshs

        except Exception as e:
            logging.exception(f'Background check_for_new_alerts() error: {e}')


# --- Background thread function ---
def background_worker():
    global last_run
    while True:
        now = time.time()
        if now - last_run >= CHECK_INTERVAL:
            last_run = now
            check_for_new_alerts()
        time.sleep(5)


# --- Start background thread when app starts ---
threading.Thread(target=background_worker, daemon=True).start()

# THE HTTP APPLICATION
app = Bottle()

# --- Route: lightweight, non-blocking ---
@app.route('/new')
@view('new_alerts')
def new_alerts():
    global for_view

    logging.info('/new route requested - lightweight response')
    # Just render whatever was last collected
    return dict(xalerts=for_view)


@app.route('/email')
def redirect_email():
    email = request.query.get('to')
    subject = request.query.get('subject', '')
    body = urlencode( request.query.get('body', '') )
    mailto = f"mailto:{email}?subject={subject}&body={body}"
    redirect(mailto)


if __name__ == '__main__':
    run( app=app, host='0.0.0.0', port=8000, debug=False, reloader=False )
