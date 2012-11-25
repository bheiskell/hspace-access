'''
@author: Benjamin Heiskell
'''
 
import ftdi
import time
import thread
import logging

from flask import Flask, render_template, url_for, request, redirect
app = Flask(__name__)

CTS=0x08 # CTS (brown wire on FTDI cable) 
RXT=0x02 # CTS (brown wire on FTDI cable) 

LOG=logging.getLogger(__name__)
 
is_closed=False
toggle_door=False

@app.route('/')
def index():
	global is_closed
	global toggle_door

	return render_template('index.html', is_opened=(not is_closed), toggle_door=toggle_door)

@app.route('/garage/', methods=['GET', 'POST'])
def garage():
	global is_closed
	global toggle_door

	if request.method == 'GET':
		return "%s" % is_closed
	else:
		toggle_door = (not toggle_door)
		return redirect(url_for('index'))

@app.route('/refresh/')
def refresh():
	return redirect(url_for('index'))

def run_http():
	app.run(host='0.0.0.0')

# run the HTTP server in a background thread
thread.start_new_thread(run_http, ())

# initialize to the ftdi device
ftdic = ftdi.ftdi_context()
ftdi.ftdi_init(ftdic)
ftdi.ftdi_usb_open(ftdic, 0x0403, 0x6001)
ftdi.ftdi_enable_bitbang(ftdic, RXT | CTS)

while True:
	result = " "
	ftdi.ftdi_read_pins(ftdic, result)

	was_closed = is_closed
	is_closed = 0 != ord(result) & RXT

	if was_closed != is_closed:
		with open ('status', 'w') as f: \
			f.write ('closed' if is_closed else 'open')

	LOG.info("Full: %s\t Masked: %s\t Is Closed: %s\t To Write: %s", \
		hex(ord(result)),
		hex(ord(result) & RXT),
		is_closed,
		hex(ord(result) | CTS)
	)

	opening=False
	if toggle_door:
		LOG.info("Opening Door")
		opening = True
		# activating the relay
		ftdi.ftdi_write_data(ftdic, chr(ord(result) | CTS), 1)

	time.sleep(3)

	if toggle_door and opening:
		# trying to work with the existing result variable has strange
		# behavior - rereading the pins
		new_result = " "
		ftdi.ftdi_read_pins(ftdic, new_result)

		LOG.info("... %s vs %s & %s = %s", \
			hex(ord(result)),
			hex(ord(new_result)),
			hex(~CTS),
			hex(ord(new_result) & (~CTS))
		)

		# resetting the relay
		ftdi.ftdi_write_data(ftdic, chr(ord(new_result) & ((~CTS) & (~RXT))), 1)

		toggle_door = False
		opening = False

ftdi.ftdi_usb_close(ftdic)
