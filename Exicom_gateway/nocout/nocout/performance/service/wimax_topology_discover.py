"""
wimax_topology_discovery.py
=======================

This file contains the code for extracting and collecting the data for wimax topology and storing this data into embeded mongodb database.

"""

from nocout_site_name import *
import socket,json
import time
import imp

utility_module = imp.load_source('utility_functions', '/omd/sites/%s/nocout/utils/utility_functions.py' % nocout_site_name)
mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)



class MKGeneralException(Exception):
    """
    Class defination for the Exception Class.
    Args: Exception object
    Kwargs: None
    Return: message
    Exception :None

    """
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

def topology_discovery_data(site,hostlist,mongo_host,mongo_port,mongo_db_name):
	"""
	inventory_perf_data : Function for collecting the data for inventory serviecs.Service state is also retunred for those services
	Args: site (site on poller on which devices are monitored)
	Kwargs: hostlist (all host on that site)

	Return : None
	Raises: No Exception
	"""

	invent_check_list = []
	ss_sec_id = []
	invent_service_dict = {}
	matching_criteria = {}
	db = mongo_module.mongo_conn(host = mongo_host,port = mongo_port,db_name =mongo_db_name)
	service = "wimax_topology"

	for host in hostlist:
		query_string = "GET services\nColumns: service_state plugin_output host_address\n" + \
		"Filter: service_description = %s\nFilter: host_name = %s\nOutputFormat: json\n" % (service,host[0])
		query_output = json.loads(utility_module.get_from_socket(site,query_string).strip())
		print query_output[0][1],"jcfkdjvfk"
		try:
			if query_output[0][1]:
				plugin_output = (query_output[0][1].split('- ')[1])
				plugin_output =	[mac for mac in plugin_output.split(' ')]
				print plugin_output
				ss_mac  = map(lambda x: x.split('=')[0],plugin_output)
				print ss_mac
				ss_ip  = map(lambda x: x.split('=')[1].split(',')[7],plugin_output)
				print ss_ip
				ss_sec_id  = map(lambda x: x.split('=')[1].split(',')[6],plugin_output)
				print ss_sec_id
				service_state = (query_output[0][0])
				print service_state
				if service_state == 0:
					service_state = "OK"
				elif service_state == 1:
					service_state = "WARNING"
				elif service_state == 2:
					service_state = "CRITICAL"
				elif service_state == 3:
					service_state = "UNKNOWN"
				host_ip = str(query_output[0][2])
				ds="topology"
				print plugin_output, ss_mac, ss_ip, ss_sec_id, service_state, host_ip
			else:
				continue
		except:
			continue
		current_time = int(time.time())
		print current_time
		topology_dict = dict (sys_timestamp=current_time,check_timestamp=current_time,device_name=str(host[0]),
				service_name=service,sector_id=ss_sec_id,
				connected_device_ip=ss_ip,
				connected_device_mac=ss_mac,data_source=ds,site_name=site,ip_address=host_ip)
		print topology_dict
		matching_criteria.update({'device_name':str(host[0]),'service_name':service})
		mongo_module.mongo_db_update(db,matching_criteria,topology_dict,"wimax_topology")
		#mongo_module.mongo_db_insert(db,topology_dict,"inventory_services")
		matching_criteria ={}
		ss_sec_id= []
		ss_ip = []
		ss_mac = []

def topology_discovery_data_main():
	"""
	inventory_perf_data_main : Main Function for data extraction for inventory services.Function get all configuration from config.ini
	Args: None
	Kwargs: None

	Return : None
	Raises: No Exception
	"""
	try:
		configs = config_module.parse_config_obj()
		desired_site = filter(lambda x: x == nocout_site_name, configs.keys())[0]
		desired_config = configs.get(desired_site)
		site = desired_config.get('site')
		mongo_host = desired_config.get('host')
                mongo_port = desired_config.get('port')
                mongo_db_name = desired_config.get('nosql_db')
		query = "GET services\nColumns: host_name\nFilter: service_description = wimax_topology\nOutputFormat: json\n"
		output = json.loads(utility_module.get_from_socket(site,query))
		print output,"hfirdhgi"
		print mongo_db_name,"vjghfbjhg"
		topology_discovery_data(site,output,mongo_host,int(mongo_port),mongo_db_name)
	except SyntaxError, e:
		raise MKGeneralException(("Can not get performance data: %s") % (e))
	except socket.error, msg:
		raise MKGeneralException(("Failed to create socket. Error code %s Error Message %s:") % (str(msg[0]), msg[1]))
if __name__ == '__main__':
	topology_discovery_data_main()	
		
				
