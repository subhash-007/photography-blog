#from wato import defaults
import logging
import os


def nocout_log():
	"""
	Handles logging functionality for device app

	Returns:
	        Returns the logger object, which logs the
		activities to a file
	"""
	logger=logging.getLogger('nocout_da')
	os.system('mkdir -p /tmp/nocout_da')
	os.system('chmod 777 /tmp/nocout_da')
	os.system('mkdir -p /tmp/nocout_da/%s' % 'ospf1_slave_1')
	fd = os.open('/tmp/nocout_da/%s/nocout_live.log' % 'ospf1_slave_1', os.O_RDWR | os.O_CREAT)
	if not len(logger.handlers):
		logger.setLevel(logging.DEBUG)
		handler=logging.FileHandler('/tmp/nocout_da/%s/nocout_live.log' % 'ospf1_slave_1')
		formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(lineno)d - %(message)s') #%(levelname)s
		handler.setFormatter(formatter)
		handler.setFormatter(formatter)
		logger.addHandler(handler)
	os.close(fd)

	return logger
