"""
File_name : rrd_main.py
Content: rrd_main file extracts the all devices and associated services with them for that particular poller and pass the host list and
         services configured on those devices to another function which calculates the services data and stores into mongodb.

"""

from nocout_site_name import *
import rrd_migration
import socket
import json
import imp
from itertools import groupby

config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

class MKGeneralException(Exception):
    """
        This is the Exception class handing exception in this file.
	Args: Exception instance

	Kwargs: None

	return: class object

    """
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason


def get_host_services_name(site_name=None, mongo_host=None, mongo_db=None, mongo_port=None):
	"""
	Function_name : get_host_services_name (extracts the services monitotred on that poller)

	Args: site_name (poller on which monitoring data is to be collected)

	Kwargs: mongo_host(host on which we have to monitor services and collect the data),mongo_db(mongo_db connection),
	        mongo_port( port for the mongodb database)
	Return : None

	raise 
	     Exception: SyntaxError,socket error 
	"""
        try:
            network_perf_query = "GET hosts\nColumns: host_name host_address host_state last_check host_last_state_change host_perf_data\nOutputFormat: json\n"
            service_perf_query = "GET services\nColumns: host_name host_address service_description service_state "+\
			    "last_check service_last_state_change service_perf_data\nFilter: service_description ~ _invent\n"+\
			    "Filter: service_description ~ _status\nFilter: service_description ~ Check_MK\nFilter: service_description ~ wimax_topology\nFilter: service_description ~ cambium_topology_discover\nOr: 5\nNegate:\nOutputFormat: json\n"
            nw_qry_output = json.loads(get_from_socket(site_name, network_perf_query))
	    print 'NW qry OUT --'
	    print nw_qry_output
            serv_qry_output = json.loads(get_from_socket(site_name, service_perf_query))
	    print 'Serv qry OUT --'
	    print serv_qry_output
	    # Group service perf data host-wise
	    serv_qry_output = sorted(serv_qry_output, key=lambda k: k[0])
	    for host, group in groupby(serv_qry_output, key=lambda e: e[0]):
		    # Find the entry in network perf data, for this host
		    nw_entry = filter(lambda t: host == t[0], nw_qry_output)
		    #print 'nw_entry -----'
		    #print nw_entry
		    serv_entry = list(group)
		    rrd_migration.build_export(
			    site_name,
			    host,
			    nw_entry[0][1],
			    nw_entry,
			    serv_entry,
			    mongo_host,
			    mongo_db,
			    mongo_port
			    )	
        except SyntaxError, e:
            raise MKGeneralException(("Can not get performance data: %s") % (e))
        except socket.error, msg:
            raise MKGeneralException(("Failed to create socket. Error code %s Error Message %s:") % (str(msg[0]), msg[1]))
        except ValueError, val_err:
		print 'Error in serv/nw qry output'
		print val_err.message

def get_from_socket(site_name, query):
    """
	Function_name : get_from_socket (collect the query data from the socket)

	Args: site_name (poller on which monitoring data is to be collected)

	Kwargs: query (query for which data to be collectes from nagios.)

	Return : None

	raise 
	     Exception: SyntaxError,socket error 
    """
    socket_path = "/omd/sites/%s/tmp/run/live" % site_name
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(socket_path)
    s.send(query)
    s.shutdown(socket.SHUT_WR)
    output = ''
    while True:
     out = s.recv(100000000)
     out.strip()
     if not len(out):
     	break
     output += out

    return output


    
if __name__ == '__main__':
    """
    main function for this file which is called in 5 minute interval.Every 5 min interval calculates the host configured on this poller
    and extracts data

    """
    configs = config_module.parse_config_obj()
    desired_site = filter(lambda x: x == nocout_site_name, configs.keys())[0]
    desired_config = configs.get(desired_site)
    site = desired_config.get('site')
    get_host_services_name(
    site_name=site,
    mongo_host=desired_config.get('host'),
    mongo_db=desired_config.get('nosql_db'),
    mongo_port=desired_config.get('port')
    )
    
