"""
nocout.py
=========

Device App web services to Create/Update/Delete a host/service into Nagios
monitoring core.
"""
import requests
from configobj import ConfigObj
from wato import *
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
from pprint import pformat
#from bulk_setconfig import generic_config,mysql_conn
from pysnmp.hlapi import *
nocout_site_name= 'ospf1_slave_1'
logger = nocout_log()
sys.path.insert(0, '/omd/sites/ospf1_slave_1/nocout')
config = ConfigObj("/omd/sites/ospf1_slave_1/share/check_mk/web/htdocs/conf.ini")
#site_config = generic_config()
from datetime import datetime
#logger.info(site_config)

hosts_file = wato_root_dir + "hosts.mk"
rules_file = wato_root_dir + "rules.mk"
default_checks_file = wato_root_dir + "nocout_default_checks.py"    # File containing default checks to be written to rules.mk
nocout_sync_pid_file = cmk.paths.tmp_dir + "nocout_sync.pid"

nocout_replication_paths = [
    ( "dir",  "check_mk",   wato_root_dir ),
    ( "dir",  "multisite",  multisite_dir ),
    ( "file", "htpasswd",   cmk.paths.htpasswd_file ),
    ( "file", "auth.secret",  '%s/auth.secret' % os.path.dirname(cmk.paths.htpasswd_file) ),
    ( "file", "auth.serials", '%s/auth.serials' % os.path.dirname(cmk.paths.htpasswd_file) ),
    ( "dir", "usersettings", cmk.paths.var_dir + "/web" ),
]
nocout_backup_paths = nocout_replication_paths + [
    ( "file", "sites",      sites_mk)
]


host_tags = {
    "snmp": "snmp-only|snmp",
    "cmk_agent": "cmk-agent|tcp",
    "snmp-v1|snmp": "snmp-v1|snmp",
    "snmp-v2|snmp": "snmp-v2|snmp",
    "v3|snmp": "v3|snmp",
    "dual": "snmp-tcp|snmp|tcp",
    "ping": "ping"
}

g_host_vars = {
    "FOLDER_PATH": "",
    "ALL_HOSTS": ALL_HOSTS, # [ '@all' ]
    "all_hosts": [],
    "clusters": {},
    "ipaddresses": {},
    "ipv6addresses": {},
    "explicit_snmp_communities":{},
    "extra_host_conf": { "alias" : [] },
    "extra_service_conf": { "_WATO" : [] },
    "host_attributes": {},
    "host_contactgroups": [],
    "_lock": False,
}

g_service_vars = {
    "only_hosts": None,
    "ALL_HOSTS": [],
    "host_contactgroups": [],
    "bulkwalk_hosts": [],
    "extra_host_conf": {},
    "extra_service_conf": {
        "retry_check_interval": [],
        "max_check_attempts": [],
        "normal_check_interval": []
    },
    "static_checks": {},
    "ping_levels": [],
    "checks": [],
    "snmp_ports": [],
    "snmp_communities": []
}

g_default_check_vars = {
		"checks": [],
		"snmp_ports": [],
		"snmp_communities": [],
		"extra_service_conf": {
			"retry_check_interval": [],
			"max_check_attempts": [],
			"normal_check_interval": []
			}
		}

interface_oriented_services = [
		'cambium_ul_rssi',
		'cambium_ul_jitter',
		'cambium_reg_count',
		'cambium_rereg_count',
		'cambium_ss_connected_bs_ip_invent'
		]

def main():

    response = ''
    action = ''
    action = html.var('mode')
    host = html.var('device_name')

    if action == 'sync':
        response = sync()

    html.write(pprint.pformat(response))


def sync():
    logger.debug('[-- sync --]')
    sites_affected = []
    # sites for which sync is unsuccessful
    dirty_sites = {}
    response = {
        "success": 1,
        "message": "Config pushed to "
    }
    # Create an archive of current folder state, to be used for rollback
    os.chdir('/omd/sites/ospf1_slave_1/etc/check_mk/conf.d/wato/')
    out = tarfile.open('/omd/sites/ospf1_slave_1/etc/check_mk/conf.d/wato_backup.tar.gz', mode='w:gz')
    try:
        for entry in os.listdir('.'):
            if entry not in ['..', '.']:
                out.add(entry)
    except Exception, err:
        logger.error('Error in tarfile generation: ' + pprint.pformat(err))
        # Doing the operation without creating backup in this case
    finally:
        out.close()

    nocout_sites = nocout_distributed_sites()
    #nocout_sites = extract_affected_sites()
    logger.debug('Nocout_sites: ' + pprint.pformat(nocout_sites))

    # Remove master_UA from nocout_sites, we dont need to push conf to master_UA
    nocout_sites = dict(filter(lambda d: d[1].get('replication') == 'slave', nocout_sites.items()))
    #logger.debug('Slave sites to push data to - ' + pprint.pformat(nocout_sites))

    try:
        bulk_add_host()
	#sync_processed(status_data)
    except Exception, e:
        logger.error('Error in make_hosts or make_rules: ' + pprint.pformat(e))
        return response

    try:
        f = os.system('~/bin/cmk -R')
        logger.debug('f : '  + pprint.pformat(f))
    except Exception, e:
        logger.error('[sync]' + pprint.pformat(e))
    # Some syntax error with hosts.mk or rules.mk
    if f != 0:
        logger.info("Could not cmk -R master_UA")
	status_data = 'update'
        return response
    status_data = 'update'
    logger.info("api-response %s " %response)
    #sync_processed(status_data)
    return response

def sync_processed(insert_status):
    try:
    	cnx = mysql_conn(site_config)
    	cursor = cnx.cursor()
    	if insert_status == "insert":
	    insert_data = '''insert into inventory_sync_status(isProcessed,createdAT,updatedAT)
                       VALUES(%s,%s,%s)'''
            cursor.execute(insert_data, (1,int(time.time()),int(time.time())))
            cnx.commit()
    	else:
	    update_data = '''update inventory_sync_status set isProcessed=0,updatedAT= %s''' %(int(time.time()))
            cursor.execute(update_data)
            cnx.commit()
        cursor.close()
        cnx.close()
	

    except Exception, e:
        logger.error('[insert_error]' + pprint.pformat(e))


def nocout_synchronize_site(site, site_attrs, restart):
    """
        Not implemented
    """
    response_text = nocout_push_snapshot_to_site(site, site_attrs, True)

    return response_text


def nocout_distributed_sites():
	"""
		nocout_distributed_sites() function
			load sites.mk to nocout_site_vars;

		Returns : Site name

	"""
	logger.debug('[nocout_distributed_sites]')
	nocout_site_vars = {
        "sites": {}
	}
	sites_file = cmk.paths.default_config_dir + "/multisite.d/sites.mk"
	if os.path.exists(sites_file):
		execfile(sites_file, nocout_site_vars, nocout_site_vars)
	logger.debug('Slave sites to push data to - ' + pprint.pformat(nocout_site_vars.get('sites')))
	logger.debug('[--]')

	return nocout_site_vars.get('sites')


def load_file(file_path):
    '''
		load_file() function loads hosts.mk file from the file path passed to it;
			stores file data in global dictionary g_host_vars;

		Raises : IOError  ; no action
	'''

    global g_host_vars
    #Reset the global vars
    g_host_vars = {
        "FOLDER_PATH": "",
        "ALL_HOSTS": ALL_HOSTS, # [ '@all' ]
        "all_hosts": [],
        "clusters": {},
        "ipaddresses": {},
        "extra_host_conf": { "alias" : [] },
        "extra_service_conf": { "_WATO" : [] },
        "host_attributes": {},
        "host_contactgroups": [],
        "_lock": False,
    }
    try:
        execfile(file_path, g_host_vars, g_host_vars)
        del g_host_vars['__builtins__']
    except IOError, e:
        pass


def save_host(file_path):
    """
		save_host() function clear the contents of old hosts.mk file and write data stored in global dictionary g_host_vars to hosts.mk and returns true/false;

		Returns : True

		Raises Exception (OSError); logs into logfile
    """
    global g_host_vars
    #Erase the file contents first
    open(file_path, 'w').close()
    try:
        f = os.open(file_path, os.O_RDWR)
    except OSError, e:
	    logger.error('Could not open rules file: ' + pprint.pformat(e))

    fcntl.flock(f, fcntl.LOCK_EX)
    os.write(f, "# encoding: utf-8\n\n")

    os.write(f, "\nhost_contactgroups += [\n")
    for host_contactgroup in g_host_vars.get('host_contactgroups'):
        os.write(f, pprint.pformat(host_contactgroup))
        os.write(f, ",\n")
    os.write(f, "]\n\n")

    os.write(f, "all_hosts += [\n")

    for host in g_host_vars.get('all_hosts'):
        os.write(f, pprint.pformat(host))
        os.write(f, ",\n")
    os.write(f, "]\n")

    os.write(f, "\n# Explicit IP addresses\n")
    os.write(f, "ipaddresses.update(")
    os.write(f, pprint.pformat(g_host_vars.get('ipaddresses')))
    os.write(f, ")")
    os.write(f, "\n\n")

    os.write(f, "host_attributes.update(\n%s)\n"
        % pprint.pformat(g_host_vars.get('host_attributes'))
    )
    os.close(f)

    return True

def nocout_add_host_attributes(host_attrs, host_edit=False):
    '''
		nocout_add_host_attributes() function add device attributes to global dictionary g_host_vars;
			if host_edit is passed to True , device type is fetched from g_host_vars dictionary and appended to host_attrs;
			filters g_host_vars removing host for which attributes are to be added;
			update all other list of g_host_vars to add the attribute

    '''
    global host_tags
    if host_edit:
	    old_entry = filter(lambda t: re.match('\b%s\b' % host_attrs.get('host'), t), g_host_vars['all_hosts'])
	    host_attrs.update({
		    'device_type': old_entry[0].split('|')[1]
		    })
    # Filter out the host's old config
    g_host_vars['all_hosts'] = filter(lambda t: not re.match('\b%s\b' % host_attrs.get('host'), t), g_host_vars['all_hosts'])

    host_entry = "%s|%s|%s|wan|prod|%s|site:%s|wato|//" % (
    host_attrs.get('host'), host_attrs.get('device_type'), host_attrs.get('mac'), host_tags.get(html.var('agent_tag'), 'snmp'), host_attrs.get('site'))
    # Find all the occurences for sub-string '|'
    all_indexes = [i for i in range(len(host_entry)) if host_entry.startswith('|', i)]
    # Insert the name of the parent device, as an auxiliary tag for the host, after the third occurence of '|'
    if host_attrs.get('parent_device_name'):
	    host_entry = host_entry[:(all_indexes[2] + 1)] + str(host_attrs.get('parent_device_name')) + \
			    '|' + host_entry[(all_indexes[2] + 1):]

    g_host_vars['all_hosts'].append(host_entry)

    g_host_vars['ipaddresses'].update({
        host_attrs.get('host'): host_attrs.get('attr_ipaddress')
    })
    g_host_vars['host_attributes'].update({
        host_attrs.get('host'): {
            'alias': host_attrs.get('attr_alias'),
            'contactgroups': (True, ['all']),
            'ipaddress': host_attrs.get('attr_ipaddress'),
            'site': host_attrs.get('site'),
            'tag_agent': host_tags.get(html.var('agent_tag'))
        }
    })


def delete_devicetype_tag(hostname=None, devicetype_tag=None):
    """
        Not implemented
    """
    local_host_vars = {
        "FOLDER_PATH": "",
        "ALL_HOSTS": ALL_HOSTS, # [ '@all' ]
        "all_hosts": [],
        "clusters": {},
        "ipaddresses": {},
        "extra_host_conf": { "alias" : [] },
        "extra_service_conf": { "_WATO" : [] },
        "host_attributes": {},
        "host_contactgroups": [],
        "_lock": False,
    }
    try:
        execfile(hosts_file, local_host_vars, local_host_vars)
	desired_host_row = filter(lambda t: re.match(hostname, t), local_host_vars['all_hosts'])
	if desired_host_row:
		remaining_hosts = filter(lambda t: not re.match(hostname, t), local_host_vars['all_hosts'])
		for tag in devicetype_tag:
			desired_host_row[0].replace(tag, '')
		remaining_hosts.extend(desired_host_row)
		save_host(hosts_file)
    except IOError, e:
	    logger.error('Could not read hosts.mk for delete devicetype tag: ' + pprint.pformat(e))



def nocout_find_host(host):
    '''
		nocout_find_host() function intialize a local dictionary local_host_vars
			initialize new_host' to True
			stores data in hosts.mk file to local dictionary local_host_vars
			check if  device name is present in local_host_vars dictionary's 'all_hosts' list;
			if  device name is present sets 'new_host' to False

		Returns : Boolean True/False

		Raises Exception (IOError); no action
    '''

    new_host = True
    ALL_HOSTS = None
    local_host_vars = {
        "FOLDER_PATH": "",
        "ALL_HOSTS": ALL_HOSTS, # [ '@all' ]
        "all_hosts": [],
        "clusters": {},
        "ipaddresses": {},
        "extra_host_conf": { "alias" : [] },
        "extra_service_conf": { "_WATO" : [] },
        "host_attributes": {},
        "host_contactgroups": [],
        "_lock": False,
    }
    try:
        execfile(hosts_file, local_host_vars, local_host_vars)
	if filter(lambda t: re.match(host, t), local_host_vars['all_hosts']):
		new_host = False
    except IOError, e:
        pass

    return new_host

def give_permissions(file_path):
    '''
		give_permissions() function opens file passed in file_path if present or create new file;
			and give file permissions to apache user group (rwx)
    '''
    try:
    	import grp
   	fd = os.open(file_path, os.O_RDWR | os.O_CREAT)
    	# Give file permissions to apache user group
    	#gid = grp.getgrnam('www-data').gr_gid
    	os.chmod(file_path, 0775)
    	os.close(fd)
    except IOError, e:
        logger.info("error in permission %s " %(e))

def bulk_add_host():
    #10|lan|ip-v4|snmp|snmp-only|ip-v4-only|prod|site:ospf1_slave_1|wato|/" + FOLDER_PATH + "/"

    try:
        all_hosts, ipaddresses,ipv6addresses,explicit_snmp_communities, host_attributes = [], {}, {},{},{}
        snmptrapd_data = []
	default_communities = []
	get_data_conf= config.get('Get Data')
	url = get_data_conf['get_data_url']
	logger.info("get_data_url % s" %url)
	auth_detail = auth()
	logger.info("auth_detail %s" %auth_detail)
	if auth_detail:
	    headers = {
		    "token":auth_detail['access_token'],
		    "user_key":auth_detail['user_key'],
	            "user_id":auth_detail['user_id']
		    }
            payload = {
                        "status_type":1,
                        "limit":10000,
                        "offset":0,
                        "in_condition":'',
                         }

	    response = requests.post(str(url),headers=headers,data= payload)
	    res = json.loads(response.content)
	    logger.info(res)
	    data = res["object"]
	    logger.info("api updated data**************************** %s "%data)

	if data:
		logger.debug("data*********** %s " %data)

                for device in data:
                   # print "key,value",device['ip']
		    keys = device["property_alias"].split("*&$%")
                    values = device["property_value"].split("*&$%")
                    properties_id = device["property_id"].split("*&$%")
		    data_dict = dict(zip(keys, zip(values,properties_id)))
                   	#{u'alias': u'EXICOM201', u'ip': u'', u'mac': u'', u'device_id': u'2', u'device_name': u'EXICOM201'}
		    logger.info("data_dict is %s" %data_dict)
                    if device.get("comunity_version", None).lower() == 'v2c' or device.get("comunity_version", None).lower() == 'v1':
			entry = str(int(device['device_id'])) + '|'+ str(device['model']) +"|"+data_dict['IP_Type'][0]+'|snmp|snmp-only|'+ data_dict['IP_Type'][0]+'-only'  +  '|wan|prod|' + 'site:ospf1_slave_1'  + '|wato|//'
			snmp_communities = device["comunity_string"]
			logger.info("entry %s and snmp_communities is %s" %(entry,snmp_communities))
                        #entry = str(device['device_id']) + '|' + str(device['model'])  + '|wan|prod|' + 'snmp-'+str(device["comunity_version"])+'|snmp' + '|site:ospf1_slave_1'  + '|wato|//'
                    elif device.get("comunity_version", None).lower() == "v3":
			
                        if data_dict["Security_Name"][0] != '' and data_dict["V3_Security_Model"][0] == "Authentication and Privacy":
			    entry = str(int(device['device_id'])) + '|'+ str(device['model'])+"|"+data_dict['IP_Type'][0]+'|snmp|snmp-only|'+ data_dict['IP_Type'][0]+'-only'  +  '|wan|prod|'+ 'site:ospf1_slave_1'  + '|wato|//'
                            snmptrapd_data = get_engine_id(data_dict,device["ip"],snmptrapd_data,auth_detail,device['device_id'],device['is_engine_id_updated'])
                            snmp_communities = ("authPriv" , str(data_dict["Auth_Protocol"][0]) ,str(data_dict['Security_Name'][0]),str(data_dict["Auth_Password"][0]),str(data_dict["Privacy_Protocol"][0]),str(data_dict["Privacy_Password"][0]))
                        elif data_dict["Security_Name"][0] != '' and data_dict["V3_Security_Model"][0] == "Authentication and No Privacy":
                            entry = str(int(device['device_id'])) + '|'+ str(device['model']) +"|"+data_dict['IP_Type'][0]+'|snmp|snmp-only|'+ data_dict['IP_Type'][0]+'-only'   +  '|wan|prod|'+ 'site:ospf1_slave_1'  + '|wato|//'

                            snmptrapd_data = get_engine_id(data_dict,device["ip"],snmptrapd_data,auth_detail,device['device_id'],device['is_engine_id_updated'])
                            snmp_communities = ("authNoPriv" , str(data_dict["Auth_Protocol"][0]) ,str(data_dict['Security_Name'][0]),str(data_dict["Auth_Password"][0]))
                        elif data_dict["Security_Name"][0] != '' and data_dict["V3_Security_Model"][0] == "No Authentication and No Privacy" :
			    logger.info("*****************************")
                            entry = str(int(device['device_id'])) + '|'+ str(device['model']) +"|"+data_dict['IP_Type'][0]+'|snmp|snmp-only|'+ data_dict['IP_Type'][0]+'-only'   +  '|wan|prod|' + 'site:ospf1_slave_1'  + '|wato|//'
                            snmptrapd_data = get_engine_id(data_dict,device["ip"],snmptrapd_data,auth_detail,device['device_id'],device['is_engine_id_updated'])
                            snmp_communities = ("noAuthNoPriv" , str(data_dict['Security_Name'][0]))
			logger.info("entry %s and snmp_communities is %s" %(entry,snmp_communities))
                    all_hosts.append(str(entry))
		    explicit_snmp_communities.update({str(device['device_id']):snmp_communities})
		    
                    if data_dict['IP_Type'][0].lower() == 'ip-v4':
                    	ipaddresses.update({str(device['device_id']): str(device['ip'])})
			host_attributes.update({ str(device['device_id']): {
                            'alias': str(device['device_name']),
			    'hostname': str(device['device_id']),
                            'ipaddress': str(device['ip']),
			    'site': 'ospf1_slave_1',
                            'snmp-community':snmp_communities,
                            'tag_agent': 'snmp',
			    'tag_address_family':'ipv4'
                        }})
		    elif data_dict['IP_Type'][0].lower() == 'ip-v6':
			ipv6addresses.update({str(device['device_id']): str(device['ip'])})
                        host_attributes.update({ str(device['device_id']): {
    	                    'alias': str(device['device_name']),
			    'hostname': str(device['device_id']),
			    'site': 'ospf1_slave_1',
                            'ipv6address':str(device['ip']),
           	            'snmp-community': snmp_communities,
                            'tag_agent': 'snmp',
			    'tag_address_family': 'ipv6',
                        }})
                    if ('public',[device['model']],ALL_HOSTS) not in default_communities:
                        default_communities.append(('public',[device['model']],ALL_HOSTS)) 
                write_hosts_file(all_hosts,ipaddresses,ipv6addresses,explicit_snmp_communities,host_attributes)
	
    except IOError, e:
        print "value error in bulk uplode",e

    return ipaddresses,all_hosts,host_attributes

def auth():
    try:
	auth_conf= config.get('User Authentication')
	payload = {
		    "user_name":auth_conf['user_id'],
		    "password":auth_conf['password'],
		    "application_id":auth_conf['application_id']
		}
	url = auth_conf['Auth_URL']
	#data = "data=%s"%str(payload).replace("'",'"').replace(" ","")
	response = requests.post(str(url), data=payload)
	res = json.loads(response.content)
	logger.info(res)
	data = res["object"]
	#print data
	#return data
    except IOError,e:
	print "error in Auth",e
    return data

def write_snmptrapd_file(snmptrapd_data):
    try:
	if snmptrapd_data:
	    path = "/etc/snmp/snmptrapd.conf"
	    #give_permissions(path)
	    logger.info("snmptrapd_data %s " %(snmptrapd_data))
	    with open('/etc/snmp/snmptrapd.conf', 'r') as f:
		newText=f.read()
		f.close()
	    list1 =  newText.split("\n")
	    logger.info("list1 %s " %(list1))
	    count = 0
	    for s in list1:
		if "traphandle default /usr/sbin/snmptthandler" in s:
		    count = count + 1
		    break
		else:
		    count = count + 1
	    list1[count] = snmptrapd_data
	    logger.info(list1[count])
	    print list1[:count], snmptrapd_data,count
	    with open('/etc/snmp/snmptrapd.conf', 'w') as f:
		f.writelines('\n'.join(list1[:count]))
		f.write('\n')
		f.writelines('\n'.join(snmptrapd_data))
		logger.info('done snmptrapd_data write %s' %snmptrapd_data)
	    os.system("sudo service snmptrapd restart")
    except IOError,e:
        logger.info("error in logger %s " %(e))

def write_hosts_file(all_hosts, ipaddresses,ipv6addresses,explicit_snmp_communities, host_attributes):
    with open('/omd/sites/ospf1_slave_1/etc/check_mk/conf.d/wato/hosts.mk', 'w') as f:
        f.write("# encoding: utf-8\n\n")
        f.write("\nhost_contactgroups += []\n\n\n")
        f.write("all_hosts += %s\n" % pformat(all_hosts))
        f.write("\n\n# Explicit IP Addresses\n")
        f.write("ipaddresses.update(%s)\n\n" % pformat(ipaddresses))
	f.write("ipv6addresses.update(%s)\n\n" % pformat(ipv6addresses))
	f.write("explicit_snmp_communities.update(%s)\n\n" % pformat(explicit_snmp_communities))
        f.write("host_attributes.update(\n%s)\n" % pformat(host_attributes))

def write_rules_file(snmp_communities):
    with open('/omd/sites/ospf1_slave_1/etc/check_mk/conf.d/wato/rules.mk', 'r') as f:
        newText=f.read()
        f.close()
    list1 =  newText.split("\n\n")
    count = 0

    for s in list1:
	if "snmp_communities" in s:
 	    count = count + 1
	    break
	else:
	    count = count + 1
    list1[count-1] = snmp_communities
    logger.debug('snmp_communities ' + pprint.pformat(snmp_communities) + '+++++++++++++++++++++')

    with open('/omd/sites/ospf1_slave_1/etc/check_mk/conf.d/wato/rules.mk', 'w') as f:

	f.writelines('\n\n'.join(list1[:count-1]))
	f.write('\n\n')
	f.writelines("snmp_communities +=  %s\n\n" % pformat(list1[count-1]))
	logger.info('done snmp_communities write')
	#f.writelines(list1[count-1])
	#f.write('\n\n')
	f.writelines('\n\n'.join(list1[count:]))
	f.close()

def get_engine_id(data_dict,device_ip,snmp_string_list,auth_api_detail,device_id,updated_engin_id_bit):
    logger.info('********************************************updated_engin_id_bit %s ' %updated_engin_id_bit)
    try:
	    logger.info(" %s %s %s"% (data_dict,device_ip,snmp_string_list))
	    auth_protocol_details = {'md5':usmHMACMD5AuthProtocol,'sha':usmHMACSHAAuthProtocol,'noauth':usmNoAuthProtocol}
	    priv_protocol_details = {'des':usmDESPrivProtocol,'aes':usmAesCfb128Protocol,'nopriv':usmNoPrivProtocol}
	    auth_protocol = data_dict["Auth_Protocol"][0].lower()
	    priv_protocol = data_dict["Privacy_Protocol"][0].lower()
	    if auth_protocol in ["md5","sha"]:
		auth_value = auth_protocol_details[auth_protocol]
	    else:
		auth_value = usmNoAuthProtocol

	    if priv_protocol in ["des","aes"]:
		print priv_protocol
		priv_value = priv_protocol_details[priv_protocol]
	    else:
		priv_value = usmNoPrivProtocol

	    discovered_engine_id = None
	    if int(updated_engin_id_bit) == 1:
		if data_dict['IP_Type'][0].lower() == 'ip-v4':

  	        	if data_dict["V3_Security_Model"][0] == "Authentication and Privacy":
		    		errorIndication, errorStatus, errorIndex, varBinds = next(
		        	getCmd(SnmpEngine(),
		        	UsmUserData(str(data_dict["Security_Name"][0]), str(data_dict["Auth_Password"][0]),\
				str(data_dict["Privacy_Password"][0]),authProtocol=auth_value,\
				privProtocol=priv_value),
		        	UdpTransportTarget((str(device_ip), 161)),
		        	ContextData(),
		        	ObjectType(ObjectIdentity('1.3.6.1.6.3.10.2.1.1.0'))))
            		elif data_dict["V3_Security_Model"][0] == "Authentication and No Privacy":
		    		errorIndication, errorStatus, errorIndex, varBinds = next(
                        	getCmd(SnmpEngine(),
                        	UsmUserData(str(data_dict["Security_Name"][0]), str(data_dict["Auth_Password"][0]),\
				authProtocol=auth_value,privProtocol=priv_value),
                        	UdpTransportTarget((str(device_ip), 161)),
                        	ContextData(),
                        	ObjectType(ObjectIdentity('1.3.6.1.6.3.10.2.1.1.0'))))
            		else:
		    		errorIndication, errorStatus, errorIndex, varBinds = next(
                        	getCmd(SnmpEngine(),
                        	UsmUserData(str(data_dict["Security_Name"][0]),authProtocol=auth_value,privProtocol=priv_value),
                        	UdpTransportTarget((str(device_ip), 161)),
                        	ContextData(),
                        	ObjectType(ObjectIdentity('1.3.6.1.6.3.10.2.1.1.0'))))
                if data_dict['IP_Type'][0].lower() == 'ip-v6':
			
			if data_dict["V3_Security_Model"][0] == "Authentication and Privacy":
      		        	errorIndication, errorStatus, errorIndex, varBinds = next(
                	      	getCmd(SnmpEngine(),
                              	UsmUserData(str(data_dict["Security_Name"][0]), str(data_dict["Auth_Password"][0]),\
                              	str(data_dict["Privacy_Password"][0]),authProtocol=auth_value,\
                              	privProtocol=priv_value),
                       	      	Udp6TransportTarget((str(device_ip), 161)),
                       	      	ContextData(),
                              	ObjectType(ObjectIdentity('1.3.6.1.6.3.10.2.1.1.0'))))
               		elif data_dict["V3_Security_Model"][0] == "Authentication and No Privacy":
                    		errorIndication, errorStatus, errorIndex, varBinds = next(
                                getCmd(SnmpEngine(),
                        	UsmUserData(str(data_dict["Security_Name"][0]), str(data_dict["Auth_Password"][0]),\
                                authProtocol=auth_value,privProtocol=priv_value),
                        	Udp6TransportTarget((str(device_ip), 161)),
                        	ContextData(),
                        	ObjectType(ObjectIdentity('1.3.6.1.6.3.10.2.1.1.0'))))
                	else:
                    		errorIndication, errorStatus, errorIndex, varBinds = next(
                        	getCmd(SnmpEngine(),
                        	UsmUserData(str(data_dict["Security_Name"][0]),authProtocol=auth_value,privProtocol=priv_value),
                        	Udp6TransportTarget((str(device_ip), 161)),
                        	ContextData(),
                        	ObjectType(ObjectIdentity('1.3.6.1.6.3.10.2.1.1.0'))))


            	logger.info(errorIndication)
	    	if errorIndication:
		    logger.info("error %s " %(errorIndication))
		    print(errorIndication)
	    	elif errorStatus:
		    print('%s at %s' % (errorStatus.prettyPrint(),
		    errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
		    logger.info("errorstatus %s "%str(errorStatus))
	    	else:
		    for varBind in varBinds:
		        discovered_engine_id = str(varBind).split()[-1]
 		        engine_id = discovered_engine_id
		        logger.info("engine_id %s " %(discovered_engine_id))

	    	if str(data_dict["Engine_ID"][0]) == "" and discovered_engine_id: 
		    headers = {
                        "token":auth_api_detail['access_token'],
                        "user_key":auth_api_detail['user_key'],
                        "user_id":auth_api_detail['user_id']
                        }
		    
		    payload = {
                        "device_id":device_id,
                        "properties_id":data_dict['Engine_ID'][1],
			"properties_values":str(discovered_engine_id),
			"properties_name":"Engine_ID"
                        }
		    get_data_conf= config.get('update_engin')
         	    url = get_data_conf['update_engin_id']
                    #data = "data=%s"%str(payload).replace("'",'"').replace(" ","")
                    response = requests.post(str(url),headers=headers,data=payload)

            	else:
		    engine_id = data_dict["Engine_ID"][0]
		    user_entered_engine_id = engine_id
		    #sys_timestamp = datetime.now().strftime("%s")
		    logger.info("Entered engine_id : %s" % str(engine_id))
		    logger.info("Discovered engine_id : %s"%str(discovered_engine_id))
	    	sys_timestamp = datetime.now().strftime("%s")
            	if str(engine_id) != str(discovered_engine_id) and discovered_engine_id:
		     generate_engine_id_alert(device_id, device_ip, sys_timestamp)
	    	elif (str(engine_id) == str(discovered_engine_id)) or (str(data_dict["Engine_ID"][0]) == "" and discovered_engine_id) :
		     clear_engine_id_alert(device_id, device_ip, sys_timestamp)
	    else:
	        engine_id = data_dict["Engine_ID"][0]
		logger.info("Entered engine_id : %s" % str(engine_id))	

	    #snmp_string_list.append("createUser -e" + str(engine_id) + " " + str(data_dict['Security_Name'][0]) +" " + str(data_dict["Auth_Protocol"][0])+" " + str(data_dict["Auth_Password"][0])+ " " + str(data_dict["Privacy_Protocol"][0])+" " + str(data_dict["Privacy_Password"][0]))
	    
	    if  data_dict["V3_Security_Model"][0] == "Authentication and Privacy":
		snmp_string_list.append("createUser -e " + str(engine_id) + " " + str(data_dict['Security_Name'][0]) +" " + str(data_dict["Auth_Protocol"][0])+" " + str(data_dict["Auth_Password"][0])+ " " + str(data_dict["Privacy_Protocol"][0])+" " + str(data_dict["Privacy_Password"][0]))
		snmp_string_list.append("authuser log,execute,net" + " " + str(data_dict['Security_Name'][0])+ " "+"authpriv")
	    elif data_dict["V3_Security_Model"][0] == "Authentication and No Privacy":
		snmp_string_list.append("createUser -e " + str(engine_id) + " " + str(data_dict['Security_Name'][0]) +" " + str(data_dict["Auth_Protocol"][0])+" " + str(data_dict["Auth_Password"][0])+ " ")
		snmp_string_list.append("authuser log,execute,net" + " " + str(data_dict['Security_Name'][0])+ " "+"auth")
	    else:
		snmp_string_list.append("createUser -e " + str(engine_id) + " " + str(data_dict['Security_Name'][0]) +" ")
		snmp_string_list.append("authuser log,execute,net" + " " + str(data_dict['Security_Name'][0])+ " "+"noauth")
	    logger.info("get_engine_id %s" %snmp_string_list)
    except Exception, err:
        logger.error('Exception in opening backup  tarfile: ' + pprint.pformat(err))

    return snmp_string_list

def generic_config():
    site = 'ospf1_slave_1'
    config = ConfigObj('/omd/sites/ospf1_slave_1/nocout/conf.d/%s' % 'ospf1.ini')
    site_config = config.get(site)
    return site_config

def generate_engine_id_alert(device_id, device_ip, sys_timestamp) :
    logger.info("In generate_engine_id_alert")
    site_config = generic_config()
    logger.info("\n \nsite_config : %s \n\n"%str(site_config))
    db = mysql_conn(site_config, default_db = False, db_name = 'xfusion_performance_spider')
    
    select_query =  "SELECT device_id from performance_eventstatus \
                where service_name = 'Engine_ID_Mismatch' and device_id = %s " % device_id
    cursor = db.cursor()
    cursor.execute(select_query)
    data = None
    data = cursor.fetchall()
    insert_query = """ INSERT INTO performance_performanceevent 
                (device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source,rule_id,severity_colour,severity_id
                )
                VALUES('%s','Engine_ID_Mismatch','%s','%s',"Engine ID Mismatch",'%s','','','Warning','Engine_ID_Mismatch', '5','#1abc9c','6')
                """% (device_id,sys_timestamp,sys_timestamp,device_ip)
    logger.info("\n *** \n insert query : \n %s \n"% str(insert_query))
    update_query = """
                INSERT INTO performance_eventstatus
                (device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source,rule_id,severity_colour,severity_id
                )
                VALUES('%s','Engine_ID_Mismatch','%s','%s',"Engine ID Mismatch",'%s','','','Warning','Engine_ID_Mismatch', '5','#1abc9c','6')
                ON DUPLICATE KEY UPDATE
                `current_value` = VALUES(current_value) ,
                `check_timestamp` = VALUES(check_timestamp) , 
                `severity` = VALUES(severity),
                `rule_id` = VALUES(rule_id), 
                `severity_colour` = VALUES(severity_colour),
                `severity_id` = VALUES(severity_id),
                `sys_timestamp` = VALUES(sys_timestamp)
                """% (device_id,sys_timestamp,sys_timestamp,device_ip)
    logger.info("\n *** \n update_query : \n %s \n"% str(update_query))
    logger.info("Data : %s"%str(data))
    if len(data) == 0 :
        cursor.execute(insert_query)
	cursor.execute(update_query)
	db.commit()
	cursor.close()

def clear_engine_id_alert(device_id, device_ip, sys_timestamp):
    site_config = generic_config()
    db = mysql_conn(site_config, default_db = False, db_name = 'xfusion_performance_spider')
    select_query =  "SELECT id, sys_timestamp from performance_eventstatus \
                where service_name = 'Engine_ID_Mismatch' and device_id = '%s' and severity = 'Warning'" % device_id
    cursor = db.cursor()
    cursor.execute(select_query)
    data = cursor.fetchall()
    delete_query = "DELETE FROM performance_eventstatus \
                where device_id = '%s' and service_name = 'Engine_ID_Mismatch' "% (device_id)
    if len(data) > 0 :
	logger.info("Data : %s " %str(data))
	event_id = data[0][0]
	check_timestamp = data[0][1]
	#occurence -> sys 
        insert_query = 'INSERT INTO performance_performanceevent '
        insert_query += """
                (device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source,rule_id,severity_colour,
		severity_id,event_id
                )
                VALUES('%s','Engine_ID_Mismatch','%s','%s',"Engine ID Matched",'%s','','','CLEAR','Engine_ID_Mismatch', '6','#6aa84f','5', '%s')
                """% (device_id,check_timestamp,sys_timestamp,device_ip,event_id)

	cursor.execute(insert_query)
	cursor.execute(delete_query)
	db.commit()
	cursor.close()
	third_party_db = mysql_conn(site_config, default_db = False, db_name = 'exicom')
	
	third_party_cursor = third_party_db.cursor()
	insert_query_tp =  'INSERT INTO performance_performanceevent '
	insert_query_tp+= """
                (device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source,rule_id,severity_colour,
		severity_id,event_id
                )
                VALUES('%s','Engine_ID_Mismatch','%s','%s',"Engine ID Matched",'%s','','','CLEAR','Engine_ID_Mismatch', '6','#6aa84f','5', '%s')
                """% (device_id,check_timestamp,sys_timestamp,device_ip,event_id)
	
	insert_temp_data = """INSERT INTO xfusion_performance_alarm_status (alarm_id,device_id,user_id,description,clear_time) VALUES('%s','%s','System','Auto Clear','%s')"""%(event_id,device_id,sys_timestamp)
        third_party_cursor.execute(insert_query_tp)
	third_party_cursor.execute(insert_temp_data)
	third_party_db.commit()
	third_party_cursor.close()
	logger.info("\ninsert_query : \n %s"%str(insert_query))
        logger.info("\ndelete_query : \n %s"%str(delete_query))
        logger.info("\n insert_query_tp: \n %s"%str(insert_query_tp))
        logger.info("\n insert_temp_data\n %s"%str(insert_temp_data))

