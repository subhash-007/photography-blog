import requests
from configobj import ConfigObj
from wato import *
import pymongo
from pymongo import Connection
import pprint
import os
import tarfile
import shutil
import sys
import ast
from shutil import copy
from itertools import ifilterfalse
from nocout_logger import nocout_log   # Module to create Device layer integration logs at /tmp/nocout_da/ospf1_slave_1/
import json
import mysql.connector
from pprint import pformat
nocout_site_name= 'ospf1_slave_1'
logger = nocout_log()
sys.path.insert(0, '/omd/sites/ospf1_slave_1/nocout')
config = ConfigObj("/omd/sites/ospf1_slave_1/share/check_mk/web/htdocs/conf.ini")

hosts_file = root_dir + "hosts.mk"
rules_file = root_dir + "rules.mk"
default_checks_file = root_dir + "nocout_default_checks.py"    # File containing default checks to be written to rules.mk
nocout_sync_pid_file = defaults.tmp_dir + "nocout_sync.pid"

nocout_replication_paths = [
    ( "dir",  "check_mk",   root_dir ),
    ( "dir",  "multisite",  multisite_dir ),
    ( "file", "htpasswd",   defaults.htpasswd_file ),
    ( "file", "auth.secret",  '%s/auth.secret' % os.path.dirname(defaults.htpasswd_file) ),
    ( "file", "auth.serials", '%s/auth.serials' % os.path.dirname(defaults.htpasswd_file) ),
    ( "dir", "usersettings", defaults.var_dir + "/web" ),
]
nocout_backup_paths = nocout_replication_paths + [
    ( "file", "sites",      sites_mk)
]


'''
def get_site_name(site=None):
    site = defaults.omd_site
    return site


db_ops_module = imp.load_source('db_ops', '/omd/sites/%s/lib/python/handlers/db_ops.py' % get_site_name())

try:
    import nocout_settings
    from nocout_settings import _DATABASES, _LIVESTATUS
except Exception as exp:
    logger.info('Error:' + pformat(exp))
'''

def main():

    response = {
	"success": 1,
	"message": "Data fetched successfully",
	"error_message": None,
	"value": []
    }
    action = ''
    action = html.var('mode')
    if action == 'live':
	response['value'] = poll_device()
    else:
	response.update({
	    "message": "No data",
	    "error_message": "No action defined for this case"
	})

    html.write(pformat(response))

def poll_device():
    count = 0	
    site_name = 'ospf1_slave_1'
    #site_name = get_site_name()
    current_values = []
    logger.info('[Polling Iteration Start]')
    device = html.var('device_id')
    services = html.var('service_name')
    service_list = str(services).split(',')
    logger.info(service_list)
    logger.info(device)
    if 'ping' in service_list :
        service_list.remove("ping") 
    #poll_device_detail = get_poll_device()
    live_poll = {}
    try:
	    for service in service_list:
		cmd = '/omd/sites/ospf1_slave_1/bin/cmk -nvp --checks=%s %s' %(service, device)	
		#cmd = 'cmk -nvp --checks=' service device
		#logger.info(cmd)
		p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
		check_output, error = p.communicate()
		#logger.info(' Check_output: ' + str(check_output))
		try:
			if check_output:
			    if service.endswith("_invent"):
				 check_output = filter(lambda t: service in t, check_output.split('\n'))
				 check_output = ''.join(check_output[0].split('- ')[1].split(' '))
				 begin = check_output.rindex('(')
				 result = (check_output[:begin]).split(",")
				    #result = ((result.replace( '@',' '))
				    #logger.info('result     '+str(result))
				 words = [w.replace('@', ' ') for w in result]
				 live_poll[service] = words
			    else:
				 check_output = filter(lambda t: service in t, check_output.split('\n'))
				    #logger.info("check_out_put_value %s " % str(check_output))
				 check_output = ''.join(check_output[0].split('- ')[1].split(' '))
				 begin = check_output.rindex('(') + 1
				 end = check_output.rindex(')')
				 result = check_output[begin:end]
				 result = ((result.replace( ';;;;',',')).strip(",")).split(",")
				    #logger.error("result++++++++++++++++++   %s" % str(result))
				    #result = ((result.replace( '@',' '))
				 words = [w.replace('@', ' ') for w in result]
				 live_poll[service] = words
                except Exception,e:
        		print "error",e
         		logger.error("Error: %s " %str(e))
         		count += 1
         		if count == 3:
              			break
         		else:
              			pass

		
    except Exception,e:
    	 print "error",e
         logger.error("Error: %s " %str(e))

    logger.info(live_poll)
    return live_poll


