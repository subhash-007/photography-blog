"""
rrd_migration.py
================

This script collects and stores data for all services running on all configured devices for this poller.

"""

from nocout_site_name import *
import os
import demjson,json
from pprint import pformat
import re
from datetime import datetime, timedelta
import subprocess
import pymongo
import imp
import time
import socket
import json
from itertools import groupby
from logs_file_path import *
file_name = os.path.basename(__file__)
file_name = file_name.replace(".py", "")
try:
        import nocout_settings
        from nocout_settings import _LIVESTATUS, _DATABASES
except Exception, exp:
        print "I'm Exception " , exp

utility_module = imp.load_source('utility_functions', '/omd/sites/%s/nocout/utils/utility_functions.py' % nocout_site_name)
mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)

logging_module = imp.load_source('log', '/omd/sites/%s/nocout/log.py' % nocout_site_name)
network_data_values = []
service_data_values = []


def build_export(site, host, ip, nw_qry_output, serv_qry_output, mongo_host, mongo_db, mongo_port):
	"""
	Function name: build_export  (function export data from the rrdtool (which stores the period data) for all services for particular host
	and stores them in mongodb in particular structure)

	Args: site : site_name (poller name on which  deviecs are monitored)
	Kwargs: host(Device from which data to collected) , ip (ip for the device) ,mongo_host (mongodb host name ),
                mongo_db (mongo db connection),mongo_port(port for mongodb)
	Return : None
        Raises:
	    Exception: None
	"""
	global network_data_values
	global service_data_values
        age = None
	rt_min, rt_max = None, None
	rta_dict = {}
	data_dict = {
		"host": str(host),
		"service": None,
		"ds": None,
		"data": [],
		"meta": None,
		"ip_address": str(ip),
		"severity":None,
		"age": None
	}
	matching_criteria ={}
	threshold_values = {}
	severity = 'UNKNOWN'
	host_severity = 'UNKNOWN'
	db = mongo_module.mongo_conn(
	    host=mongo_host,
	    port=int(mongo_port),
	    db_name=mongo_db
	)
	print "$$$$$ nw_qry_output",nw_qry_output
	# Process network perf data
	for entry in nw_qry_output:
		threshold_values = get_threshold(entry[-1])
		rt_min = threshold_values.get('rtmin').get('cur')
		rt_max = threshold_values.get('rtmax').get('cur')
		# rtmin, rtmax values are not used in perf calc
		threshold_values.pop('rtmin', '')
		threshold_values.pop('rtmax', '')
		#print '-- threshold_values'
		#print threshold_values
		if entry[2] == 0:
			host_severity = 'UP'
		elif entry[2] == 1:
			host_severity = 'DOWN'
		# Age of last service state change
		last_state_change = entry[-2]
		current_time = int(time.time())
		age = current_time - last_state_change
		for ds, ds_values in threshold_values.items():
			check_time = datetime.fromtimestamp(entry[3]) 
			# Pivot the time stamp to next 5 mins time frame
			local_timestamp = pivot_timestamp_fwd(check_time)
			if ds == 'pl':
				ds_values['cur'] = ds_values['cur'].strip('%')
				if host_severity == 'DOWN' :
					ds_values['cur'] = '100'		
			data_values = [{'time': check_time, 'value': ds_values.get('cur')}]
			if ds == 'rta':
				rta_dict = {'min_value': rt_min, 'max_value': rt_max}
				data_values[0].update(rta_dict)
			data_dict.update({
				'site': site,
				'host': host,
				'service': 'ping',
				'ip_address': ip,
				'severity': host_severity,
				'age': age,
				'ds': ds,
				'data': data_values,
				'meta': ds_values,
				'check_time': check_time,
				'local_timestamp': local_timestamp 
				})
			matching_criteria.update({
				'host': host,
				'service': 'ping',
				'ds': str(ds)
				})
			# Update the value in status collection, Mongodb
			mongo_module.mongo_db_update(db, matching_criteria, data_dict, 'network_perf_data')
			logger.info("mongodb collection updated for network_perf_data")
			network_data_values.append(data_dict)
			data_dict = {}
	#if host_severity == 'UP':
	#	print 'network_data_values'
	#	print network_data_values
	#try:
	#	mongo_module.mongo_db_insert(db, network_data_values, 'network_perf_data')
	#except Exception, e:
	#	print e.message
	# If host is Down, do not process its service perf data
	if host_severity == 'DOWN':
		return
	data_dict = {}
	print '!!!!!!network_data_values',network_data_values
	# Process service perf data
	for entry in serv_qry_output:
		if not len(entry[-1]):
			continue
		print entry[-1]
		threshold_values = get_threshold(entry[-1])
		#print '-- threshold_values'
		#print threshold_values
		severity = calculate_severity(entry[3])
		# Age of last service state change
		last_state_change = entry[-2]
		current_time = int(time.time())
		age = current_time - last_state_change
		data_dict.update({
			'service': str(entry[2]),
			'ip_address': ip,
			'severity': severity,
			'age': age
			})
		for ds, ds_values in threshold_values.items():
			check_time = datetime.fromtimestamp(entry[4])
			# Pivot the time stamp to next 5 mins time frame
			local_timestamp = pivot_timestamp_fwd(check_time)
			data_values = [{'time': check_time, 'value': ds_values.get('cur')}]
			#print "##################### data_values------------------"
			#print data_values
############################################################ UPDATED ACCORDING TO BHUTAN #############################################################			
			service_name = entry[2].split()[0]
			#print "\nService_Name : "+service_name
			data_dict.update({
				'site': site,
				'host': host,
				'service': service_name, #entry[2]
				'ip_address': ip,
				'severity': severity,
				'age': age,
				'ds': ds,
				'data': data_values,
				'meta': ds_values,
				'check_time': check_time,
				'local_timestamp': local_timestamp 
				})
			matching_criteria.update({
				'host': host,
				'service': service_name, #entry[2]
				'ds': str(ds)
				})
#####################################################################################################################################################	

			# Update the value in status collection, Mongodb
			mongo_module.mongo_db_update(db, matching_criteria, data_dict, 'serv_perf_data')
			logger.info("mongodb collection updated for serv_perf_data")
			service_data_values.append(data_dict)
			data_dict = {}
	
	#print 'service_data_values'
	#print service_data_values
	# Bulk insert the values into Mongodb
	#try:
	#	mongo_module.mongo_db_insert(db, service_data_values, 'serv_perf_data')
	#except Exception, e:
	#	print e.message


def insert_bulk_perf(net_values, serv_values, mongo_host, mongo_port, mongo_db):
	db = mongo_module.mongo_conn(
	    host=mongo_host,
	    port=int(mongo_port),
	    db_name=mongo_db
	)

	try:
		
		mongo_module.mongo_db_insert(db, net_values, 'network_perf_data')
		logger.info('inserted record in NW perf %s',net_values)
	except Exception, e:
		logger.exception('Insert error in NW perf values %s:',str(e.message))
		print 'Insert error in NW perf values'
		print e.message

	try:
		print serv_values,"serv_values"
		mongo_module.mongo_db_insert(db, serv_values, 'serv_perf_data')
		print mongo_module,"mongo_module"
		logger.info('inserted record in Serv ')
	except Exception, e:
		logger.exception('Insert error in Serv values %s:', str(e.message))
		print 'Insert error in Serv values'
		print e.message
	logger.info("**********end 'insert_bulk_perf' function*********")


def calculate_severity(severity_bit):
	"""
	Function to compute host service states
	"""
	severity = 'UNKNOWN'
	if severity_bit == 0:
		severity = 'OK'
	elif severity_bit == 1:
		severity = 'WARNING'
	elif severity_bit == 2:
		severity = 'CRITICAL'

	return severity


def get_host_services_name(site_name=None, mongo_host=None, mongo_db=None, mongo_port=None, configs=None):
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
	    logger.info("**********start'get_host_services_name'function **********")
            network_perf_query = "GET hosts\nColumns: host_name host_address host_state last_check host_last_state_change host_perf_data\nOutputFormat: json\n"
	    logger.info("network_perf_query[%s]", network_perf_query)
            service_perf_query = "GET services\nColumns: host_name host_address service_description service_state "+\
                            "last_check service_last_state_change service_perf_data\nFilter: service_description ~ _invent\n"+\
			    "Filter: service_description ~ _status\nFilter: service_description ~ Check_MK\nFilter: service_description ~ wimax_topology\nFilter: service_description ~ cambium_topology_discover\nOr: 5\nNegate:\nOutputFormat: json\n"
	    logger.info("Service_perf_query[%s]", service_perf_query)
            nw_qry_output = json.loads(get_from_socket(site_name, network_perf_query))
	    logger.info("nw_qry_output %s:", nw_qry_output)
            #print 'NW qry OUT --'
            #print nw_qry_output
            serv_qry_output = json.loads(get_from_socket(site_name, service_perf_query))
	    logger.info("serv_qry_output %s:", serv_qry_output)
	    #print serv_qry_output,"serv_qry_output"

            device_down_query = "GET services\nColumns: host_name host_address service_state last_check service_last_state_change service_description\nFilter: service_description ~ Check_MK\nFilter: service_description ~ snmp_state\nOr: 2\nFilter: service_state = 3\nFilter: service_state = 2\nOr: 2\n"+\
                                "OutputFormat: python\n"
            device_down_output = eval(get_from_socket(site_name, device_down_query))
	    print "device_down_output",device_down_output
	    device_down_list =[str(item) for sublist in device_down_output for item in sublist] 
	    print "device_down_list",device_down_list
            device_ping_up_query = "GET services\nColumns: host_name host_address service_state last_check service_last_state_change service_description\nFilter: service_description ~ Check_MK\nFilter: service_state = 0\nFilter: service_state = 1\nOr: 2\n"+\
                                "And: 2\nFilter: last_check > 0\nOutputFormat: python\n"
	    device_ping_up_output = eval(get_from_socket(site_name, device_ping_up_query))

            print "device_ping_up_output",device_ping_up_output
            device_snmp_up_query = "GET services\nColumns: host_name host_address service_state last_check service_last_state_change service_description\nFilter: service_description ~ snmp_state\nFilter: service_state = 0\nFilter: service_state = 1\nOr: 2\n"+\
                                "And: 2\nFilter: last_check > 0\nOutputFormat: python\n"
            device_snmp_up_output = eval(get_from_socket(site_name, device_snmp_up_query))

            print "device_snmp_up_output",device_snmp_up_output
	    device_up_list = []
            up_tuple_dict = {}
	    ping_up = [item[0] for item in device_ping_up_output]
	    snmp_up = [item[0] for item in device_snmp_up_output]
	    up = list(set(ping_up).intersection(snmp_up))
	    print "UP devices",up
	    for devices in up :
	    	for snmp_up_detail in device_snmp_up_output :
		    print str(snmp_up_detail[0]) , str(devices)
		    if str(snmp_up_detail[0]) == str(devices):
			up_tuple_dict["snmp"] = snmp_up_detail
		for ping_up_detail in device_ping_up_output :
		    if str(ping_up_detail[0]) == str(devices):
			up_tuple_dict["ping"] = ping_up_detail
		if up_tuple_dict["snmp"][5] < up_tuple_dict["ping"][5]:
		    up_tuple = up_tuple_dict["snmp"]
		else :
		    up_tuple = up_tuple_dict["ping"]

		device_up_list.append(up_tuple)
	    print "qwerty", device_up_list , "---------------", device_down_output
	    write_host_status(device_down_output, device_up_list, configs)
            #print 'Serv qry OUT --'
            #print serv_qry_output
            # Group service perf data host-wise
            serv_qry_output = sorted(serv_qry_output, key=lambda k: k[0])
            #i = 0
            for host, group in groupby(serv_qry_output, key=lambda e: e[0]):
                    #i += 1
                    # Find the entry in network perf data, for this host
                    nw_entry = filter(lambda t: host == t[0], nw_qry_output)
                    #print 'nw_entry -----'
                    #print nw_entry
                    serv_entry = list(group)
                    #if i == 500:
                    #   break
                    build_export(
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
	    logger.exception("Can not get performance data: %s", str(e))
        except socket.error, msg:
            raise MKGeneralException(("Failed to create socket. Error code %s Error Message %s:") % (str(msg[0]), msg[1]))
	    logger.excepton('SocketError !,Failed to create socket.Error Code %s, Error Message %s:',str(msg[0]), msg[1])
        except ValueError, val_err:
		logger.exception('ValueError,Error in serv/nw qry output %s:',str(val_err))
                print 'Error in serv/nw qry output'
                print val_err.message
	logger.info("**********end 'get_host_services_name' function********** ")

def write_host_status(down_list,up_list,configs=None):
    """
    Function creates formatted record into for host_status and non-communicating sites of multiple devices
    Args: down_list - Raw list of down device
	  up_list - Raw list of up device
	  configs - config parameters from file
    Return : None
    """
    configs  = {'user' :configs.get('ospf1_slave_1').get('user'),
        'sql_passwd':configs.get('ospf1_slave_1').get('sql_passwd'),
        'nosql_db': configs.get('ospf1_slave_1').get('nosql_db'),
        'sql_port' : configs.get('ospf1_slave_1').get('mysql_port'),
        'sql_db' : configs.get('ospf1_slave_1').get('sql_db'), 
        'table_name' : configs.get('ospf1_slave_1').get('network_status_tables').get('table_name'), 
	'ip' : configs.get('ospf1_slave_1').get('ip')
      
}
    data = []
    events_up = []
    events_down = []
    if down_list :
	for entry in down_list :
	    last_state_change = entry[4]
	    current_time = int(time.time())
	    age = current_time - last_state_change
	    check_time = datetime.fromtimestamp(entry[3])
	    local_timestamp = pivot_timestamp_fwd(check_time)
	    local_time_epoch = utility_module.get_epoch_time(local_timestamp)
	    #data.append((entry[0],'host_status','host_status','OFF','','','',local_time_epoch,last_state_change,''))
	    events_down.append((entry[0],'Non-communicating-site',local_time_epoch,last_state_change,'Non-communicating-site',entry[1],'','','Major','Non-communicating-site','7','#e87e04','7'))
	    #print events_down, "events_down"
	if events_down :
	    insert_nc_data('performance_performanceevent',events_down,configs)
    if up_list :
        for entry in up_list :
            last_state_change = entry[4]
            current_time = int(time.time())
            age = current_time - last_state_change
            check_time = datetime.fromtimestamp(entry[3])
            local_timestamp = pivot_timestamp_fwd(check_time)
            local_time_epoch = utility_module.get_epoch_time(local_timestamp)
            #check_time_epoch = 
            #data.append((entry[0],'host_status','host_status','ON','','','',local_time_epoch,last_state_change,''))
	    data.append((entry[0],'last_packet_received','last_packet_received','ON','','','',local_time_epoch,last_state_change,''))
	    events_up.append((entry[0],'Non-communicating-site',local_time_epoch,last_state_change,'Non-communicating-site',entry[1],'','','OK','Non-communicating-site',None,None,None))
        if events_up :
	     print "events_up : \n",events_up, "\n"
	     delete_data('performance_eventstatus',events_up,configs)

    if data:
	insert_host_status_data('performance_performanceservice',data,configs)

def insert_host_status_data(table,data_values,configs):
        """
        Function insert the formatted record into mysql table for host_status of multiple devices
        Args: table (mysql table on which we have to insert the data.table information is fetched from config.ini)
        Kwargs: data_values (list of formatted doc )
        Return : None
        Raise : MYSQLdb.error


        """
        print data_values,"\n------------- data_values --------"
        #logger.info(data_values)
        db = utility_module.mysql_conn(configs=configs)
        #print "db", db
	cursor = db.cursor()
        query = 'INSERT INTO `%s` ' % table
        query += """
                (device_id,service_name,data_source,
                current_value,min_value,max_value,avg_value,
                sys_timestamp,check_timestamp,severity
                )

                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """

        update_query = """
                INSERT INTO performance_servicestatus
                (
                device_id,service_name,data_source,
                current_value,min_value,max_value,avg_value,
                sys_timestamp,check_timestamp,severity
                )
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                `current_value` = VALUES(current_value) ,
                `check_timestamp` = VALUES(check_timestamp) , 
                `severity` = VALUES(severity),
                `sys_timestamp` = VALUES(sys_timestamp)
                """
        #cursor = db.cursor()
        for values in data_values :
                        try:
                                cursor.execute(query, values)
                        except Exception,e :
                                print "Error : ",e

                        #db.commit()
                        try:
                                cursor.execute(update_query, values)
                                print "update_query",update_query,values
                        except Exception as err:
                                print "ERROR",err
        db.commit()
        cursor.close()


def delete_data(table,data_values,configs):
        #print data_values,"delete_data_values --------"
        db = utility_module.mysql_conn(configs=configs)
        cursor = db.cursor()
        for data in data_values :
	    find_event_query = """
		SELECT id,sys_timestamp, severity, severity_colour, severity_id, rule_id FROM performance_eventstatus WHERE device_id=%s and service_name='%s'
			      """%(data[0],data[1])
	    cursor.execute(find_event_query)
	    event_id = cursor.fetchall()
	    if event_id :
            delete_query = """
                DELETE FROM performance_eventstatus
                where device_id = %s and service_name = '%s' and data_source = '%s'
                """%(data[0],data[1],data[9])
		insert_tp_query = """
			INSERT INTO exicom.performance_performanceevent(device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source,rule_id,severity_colour,severity_id,event_id
                )
                VALUES(%s,'%s',%s,%s,'%s','%s','%s','%s','%s','%s',%s,'%s',%s,%s)
		"""%(data[0],data[1],event_id[0][1],data[3],data[4],data[5],event_id[0][2],data[7],'CLEAR',data[9],event_id[0][5],event_id[0][3],event_id[0][4], event_id[0][0])
                insert_query = """
                        INSERT INTO performance_performanceevent(device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source,rule_id,severity_colour,severity_id,event_id
                )
                VALUES(%s,'%s',%s,%s,'%s','%s','%s','%s','%s','%s',%s,'%s',%s,%s)
                """%(data[0],data[1],event_id[0][1],data[3],data[4],data[5],event_id[0][2],data[7],'CLEAR',data[9],event_id[0][5],event_id[0][3],event_id[0][4], event_id[0][0])

		insert_clear_alarm_status = """
			INSERT INTO exicom.xfusion_performance_alarm_status
			 (alarm_id,device_id,user_id,description,clear_time)
			VALUES(%s,%s,'%s','%s',%s)"""%(event_id[0][0],data[0],'System','Auto Clear',data[3])
            try :
                cursor.execute(delete_query)
            except mysql.connector.Error as err:
                print "DELETE MySQL ERROR",err
            db.commit()
        cursor.close()



def insert_nc_data(table,data_values,configs):
        """
        Function insert the formatted record into mysql table for multiple non-communicating devices
        Args: table (mysql table on which we have to insert the data.table information is fetched from config.ini)
        Kwargs: data_values (list of formatted doc )
        Return : None
        Raise : MYSQLdb.error


        """
        print data_values,"\n------------- data_values --------"
        #logger.info(data_values)
        db = utility_module.mysql_conn(configs=configs)
        #print "db", db
        select_query = """
                SELECT device_id from performance_eventstatus
                where service_name = 'Non-communicating-site'
                """
        cursor = db.cursor()
        cursor.execute(select_query)
        alarm_list = []
        alarms_present = cursor.fetchall()
        #print alarms_present
        for alarm in alarms_present :
                alarm_list.append(alarm[0])

        query = 'INSERT INTO `%s` ' % table
        query += """
                (device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source,rule_id,severity_colour,severity_id
                )
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """
        update_query = """
                INSERT INTO performance_eventstatus
                (device_id,service_name,sys_timestamp,check_timestamp,
                current_value,min_value,max_value,avg_value,
                severity,data_source,rule_id,severity_colour,severity_id
                )
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                `current_value` = VALUES(current_value) ,
                `check_timestamp` = VALUES(check_timestamp) , 
                `severity` = VALUES(severity),
                `rule_id` = VALUES(rule_id), 
                `severity_colour` = VALUES(severity_colour),
                `severity_id` = VALUES(severity_id),
                `sys_timestamp` = VALUES(sys_timestamp)
                """
        #cursor = db.cursor()
        for values in data_values :
                if int(values[0]) not in alarm_list :
                        try:
                                cursor.execute(query, values)
                        except Exception,e :
                                print "Error : ",e
                        except mysql.connector.Error as err:
                                print err
                                raise mysql.connector.Error, err

                        #db.commit()
                        try:
                                cursor.execute(update_query, values)
                                #print "update_query",update_query
                        except mysql.connector.Error as err:
                                print "ERROR",err
                                raise mysql.connector.Error, err

        db.commit()
        cursor.close()
     
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
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    machine = site_name[:-8]
    socket_ip = _LIVESTATUS[machine]['host']
    socket_port = _LIVESTATUS[machine][site_name]['port']
    print socket_ip, socket_port
    s.connect((socket_ip, socket_port))
    logger.info("socket connection established")
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



def get_ss(host=None, interface=None):
	ss_device = None
	global nocout_site_name
        l_host_vars = {
		    "FOLDER_PATH": "",
		    "ALL_HOSTS": '', # [ '@all' ]
		    "all_hosts": [],
		    "clusters": {},
		    "ipaddresses": {},
		    "extra_host_conf": { "alias" : [] },
		    "extra_service_conf": { "_WATO" : [] },
		    "host_attributes": {},
		    "host_contactgroups": [],
		    "_lock": False,
	}
	# path to hosts file
	hosts_file = '/omd/sites/%s/etc/check_mk/conf.d/wato/hosts.mk' % nocout_site_name
	try:
		execfile(hosts_file, l_host_vars, l_host_vars)
		del l_host_vars['__builtins__']
		
		host_row = filter(lambda t: re.match(interface, t.split('|')[2]) \
				and re.match(host, t.split('|')[3]), l_host_vars['all_hosts'])
		ss_device = host_row[0].split('|')[0]
	except Exception, e:
		return ss_device

	return ss_device


def split_service_interface(serv_disc):

	return serv_disc[:-18], serv_disc[-17:]


def do_export(site, host, file_name,data_source, start_time, serv):
    """
    Function_name : do_export (Main function for extracting the data for the services from rrdtool)

    Args: site (poller on which devices are monitored)

    Kwargs: host(Device from which data to collected) , file_name (rrd file for data source) ,data_source (service data source),
                start_time (time from which data is extracted),serv (service)
    return:
           None
    Exception:
           JSONDecodeError
    """
    data_series = {}
    cmd_output ={}
    CF = 'AVERAGE'
    resolution = '-300sec';

    # Get India times (GMT+5.30)
    utc_time = datetime(1970, 1,1, 5, 30)
    end_time = datetime.now()

    year, month, day = end_time.year, end_time.month, end_time.day
    hour = end_time.hour
    #Pivoting minutes to multiple of 2, to synchronize with rrd dump
    minute = end_time.minute - (end_time.minute % 5)
    end_time = datetime(year, month, day, hour, minute)

    if start_time is None:
        start_time = end_time - timedelta(minutes=5)
    else:
	start_time = start_time + timedelta(minutes=1)

    #end_time = datetime.now() - timedelta(minutes=10)
    #start_time = end_time - timedelta(minutes=5)
    
    start_epoch = int(time.mktime(start_time.timetuple()))
    end_epoch = int(time.mktime(end_time.timetuple()))
   
    #Subtracting 5:30 Hrs to epoch times, to get IST
    #start_epoch -= 19800
    #end_epoch -= 19800

    # Command for rrdtool data extraction
    if start_time > end_time:
	return
    cmd = '/omd/sites/%s/bin/rrdtool xport --json --daemon unix:/omd/sites/%s/tmp/run/rrdcached.sock -s %s -e %s --step 300 '\
        %(site,site, str(start_epoch), str(end_epoch))
    RRAs = ['MIN','MAX','AVERAGE']

    for RRA in RRAs:
    	cmd += 'DEF:%s_%s=%s:%d:%s XPORT:%s_%s:%s_%s '\
            %(data_source, RRA, file_name, 1, RRA, data_source,
                RRA, data_source, RRA)
    p=subprocess.Popen(cmd,stdout=subprocess.PIPE, shell=True)
    cmd_output, err = p.communicate()
    try:
        cmd_output = demjson.decode(cmd_output)
    except demjson.JSONDecodeError, e:
        return data_series

    legend = cmd_output.get('meta').get('legend')
    start_check = cmd_output['meta']['start']
    end_check = start_check+300
    start_check = datetime.fromtimestamp(start_check)
    end_check = datetime.fromtimestamp(end_check)
    local_timestamp = pivot_timestamp(start_check)

    data_series.update({
        "site": site,
        "legend": legend,
        "data" :cmd_output['data'],
        "start_time": start_check,
        "end_time": end_check,
        "check_time": start_check,
        "local_timestamp": local_timestamp
    })
    return data_series


def get_threshold(perf_data):
    """
    Function_name : get_threshold (function for parsing the performance data and storing in the datastructure)

    Args: perf_data performance_data extracted from rrdtool

    Kwargs: None
    return:
           threshold_values (data strucutre containing the performance_data for all data sources)
    Exception:
           None
    """
    #print "perf_data----threshold"
    #print perf_data
    threshold_values = {}

    if not len(perf_data):
    	return threshold_values
    for param in perf_data.split(" "):
	param = param.strip("['\n', ' ']")
	if param.partition('=')[2]:
        	if ';' in param.split("=")[1]:
            		threshold_values[param.split("=")[0]] = {
                	"war": re.sub('[ms]', '', param.split("=")[1].split(";")[1]),
                	"cric": re.sub('[ms]', '', param.split("=")[1].split(";")[2]),
                	"cur": re.sub('ms', '', param.split("=")[1].split(";")[0])
            		}
        	else:
            		threshold_values[param.split("=")[0]] = {
                	"war": None,
                	"cric": None,
                	"cur": re.sub('[ms]', '', param.split("=")[1].strip("\n"))
            		}
	else:
		threshold_values[param.split("=")[0]] = {
			"war": None,
			"cric": None,
			"cur": None
                        }
    logger.info("threshold_values %s:",threshold_values)
    return threshold_values


def pivot_timestamp(timestamp):
    """
    Function_name : pivot_timestamp (function for pivoting the time to 5 minutes interval)

    Args: timestamp

    Kwargs: None
    return:
           t_stmp (pivoted time stamp)
    Exception:
           None
    """
    t_stmp = timestamp + timedelta(minutes=-(timestamp.minute % 5))

  
    return t_stmp

def pivot_timestamp_fwd(timestamp):
    """
    Function_name : pivot_timestamp (function for pivoting the time to 5 minutes interval)

    Args: timestamp

    Kwargs: None
    return:
           t_stmp (pivoted time stamp)
    Exception:
           None
    """
    #print "Timestamp----"
    #print timestamp
    #print timestamp.minute 
    #print timedelta(minutes=-(timestamp.minute % 10))
    t_stmp = timestamp + timedelta(minutes=-(timestamp.minute % 5))
    if (timestamp.minute % 5) != 0:
    	t_stmp = t_stmp + timedelta(minutes=5)

    logger.info("**** Original time %s: ****",timestamp)
    logger.info("$$$$ Updated time  %s: $$$$",t_stmp)
    return t_stmp



def db_port(site_name=None):
    """
    Function_name : db_port (function for extracting the port value for mongodb for particular poller,As different poller will 
		    have different)

    Args: site_name (poller on which monitoring is performed)

    Kwargs: None
    return:
           port (mongodb port)
    Exception:
           IOError
    """
    port = None
    if site_name:
        site = site_name
    else:
        file_path = os.path.dirname(os.path.abspath(__file__))
        path = [path for path in file_path.split('/')]

        if len(path) <= 4 or 'sites' not in path:
            raise Exception, "Place the file in appropriate omd site"
        else:
            site = path[path.index('sites') + 1]
    
    port_conf_file = '/omd/sites/%s/etc/mongodb/mongod.d/port.conf' % site
    try:
        with open(port_conf_file, 'r') as portfile:
            port = portfile.readline().split('=')[1].strip()
    except IOError, e:
        raise IOError, e

    return port


def mongo_conn(**kwargs):
    """
    Function_name : mongo_conn (function for making mongo db connection)

    Args: site_name (poller on which monitoring is performed)

    Kwargs: Multiple arguments
    return:
           db (mongdb object)
    Exception:
           PyMongoError
    """
    DB = None
    try:
        CONN = pymongo.Connection(
            host=kwargs.get('host'),
            port=kwargs.get('port')
        )
        DB = CONN[kwargs.get('db_name')]
    except pymongo.errors.PyMongoError, e:
        raise pymongo.errors.PyMongoError, e
    return DB


def insert_data(data_dict):
    """
    Function_name : insert_data (inserting data in mongo db)

    Args: data_dict (data_dict which is inserted)

    Kwargs: None
    return:
           None
    Exception:
           None
    """
    port = None
    db  = None
    #Get the port for mongodb process, specific to this multisite instance
    port = db_port()

    #Get the mongodb connection object
    db = mongo_module.mongo_conn(
        host='localhost',
        port=int(port),
        db_name='nocout'
    )

    if db:
        db.device_perf.insert(data_dict)
	logger.info("Data Inserted into Mongodb")
        return "Data Inserted into Mongodb"
    else:
	logger.info("Data couldn't be inserted into Mongodb")
        return "Data couldn't be inserted into Mongodb"


def rrd_migration_main(site,host,services,ip, mongo_host, mongo_db, mongo_port):
	"""
	Main function for the rrd_migration which extracts and store data in mongodb databses for all services configured on all devices
	Args: site : site (poller name on which  deviecs are monitored)
        Kwargs: host(Device from which data to collected) ,services(host services) ,ip (ip for the device) ,mongo_host (mongodb host name ),
	                mongo_db (mongo db connection),mongo_port(port for mongodb)
	return:
	      None
	Raise
	    Exception : None
	"""
	build_export(site, host, ip, mongo_host, mongo_db, mongo_port)

"""if __name__ == '__main__':
    build_export('BT','AM-400','PING')
"""



def collect_data_for_wimax(host,site,db):
		matching_criteria = {}
		wimax_service_list = ['wimax_modulation_dl_fec','wimax_modulation_ul_fec','wimax_dl_intrf','wimax_ul_intrf','wimax_ss_ip','wimax_ss_mac']
                for service in wimax_service_list:
                        query_string = "GET services\nColumns: service_state service_perf_data host_address last_check\nFilter: " + \
                        "service_description = %s\nFilter: host_name = %s\nOutputFormat: json\n"                % (service,host)
                        query_output = json.loads(utility_module.get_from_socket(site,query_string).strip())
                        try:
                                if query_output[0][1]:
                                        perf_data_output = str(query_output[0][1])
                                        service_state = (query_output[0][0])
                                        host_ip = str(query_output[0][2])
					last_check = (query_output[0][3])
                                        if service_state == 0:
                                                service_state = "OK"
                                        elif service_state == 1:
                                                service_state = "WARNING"
                                        elif service_state == 2:
                                                service_state = "CRITICAL"
                                        elif service_state == 3:
                                                service_state = "UNKNOWN"
                                        perf_data = utility_module.get_threshold(perf_data_output)
                                else:
                                        continue
                        except:
                                continue
                        for datasource in perf_data.iterkeys():
				data = []
                                cur =perf_data.get(datasource).get('cur')
                                war =perf_data.get(datasource).get('war')
                                crit =perf_data.get(datasource).get('cric')
				temp_dict = dict(value = cur,time = pivot_timestamp_fwd(datetime.fromtimestamp(last_check)))
				#print pivot_timestamp_fwd(datetime.fromtimestamp(last_check)))
                                wimax_service_dict = dict (check_time=datetime.fromtimestamp(last_check),
						local_timestamp=pivot_timestamp_fwd(datetime.fromtimestamp(last_check)),host=str(host),
                                                service=service,data=[temp_dict],meta ={'cur':cur,'war':war,'cric':crit},
                                                ds=datasource,severity=service_state,site=site,ip_address=host_ip)
                                matching_criteria.update({'host':str(host),'service':service,'ds':datasource})
                                mongo_module.mongo_db_update(db,matching_criteria,wimax_service_dict,"serv_perf_data")
                                mongo_module.mongo_db_insert(db,wimax_service_dict,"serv_perf_data")
				matching_criteria = {}
                wimax_service_dict = {}


def collect_data_from_rrd(db,site,path,host,replaced_host,service,ds_index,start_time,data_dict,status_dict):

	service_data_type = {
		"radwin_rssi" : int,
		"radwin_uas"  : int,
		"radwin_uptime": int,
		"radwin_service_throughput" : float,
		"radwin_dl_utilization": int,
		"radwin_ul_utilization" : int
	}

	m = -5
	data_series = do_export(site, host, path, ds_index, start_time, service)
	if data_series is None:
		return 1
	data_dict.update({
		"check_time": data_series.get('check_time'),
		"local_timestamp": data_series.get('local_timestamp'),
		"site": data_series.get('site')
        })
	status_dict.update({
		"check_time": data_series.get('check_time'),
		"local_timestamp": data_series.get('local_timestamp'),
		"site": data_series.get('site')
        })
 
	data_dict['ds'] = ds_index

	status_dict['ds'] = ds_index
			
	ds_values = data_series['data'][:-1]

	start_time = mongo_module.get_latest_entry(db_type='mongodb', db=db, table_name=None,
                                                                host=replaced_host, serv=data_dict['service'], ds=ds_index)
	temp_dict = {}
	for d in ds_values:
		if d[-1] is not None:
			m += 5
			if service in service_data_type:
				d_type = service_data_type[service]
			else:
				d_type = float
					
			temp_dict = dict(
					time=data_series.get('check_time') + timedelta(minutes=m),
						value=d_type(d[-1]))
			# forcing to not add deuplicate entry in mongo db. currenltly suppose at time 45.00 50.00 data comes in
			# in one iteration then in second iteration 50.00 55.00 data comes .So Not adding second iteration
			# 50.00 data again.
			if ds_index == 'rta':
				temp_dict.update({"min_value":d[-3],"max_value":d[-2]}) 
			if start_time == temp_dict.get('time'):
				data_dict.update({"local_timestamp":temp_dict.get('time')+timedelta(minutes=2),
				"check_time":temp_dict.get('time')+ timedelta(minutes=2)})
				continue
			data_dict.get('data').append(temp_dict)
	if len(temp_dict):
		status_dict.get('data').append(temp_dict)
		status_dict.update({"local_timestamp":temp_dict.get('time'),"check_time":temp_dict.get('time')})


if __name__ == '__main__':
    """
    main function for this file which is called in 5 minute interval.Every 5 min interval calculates the host configured on this poller
    and extracts data

    """
    #global network_data_values
    #global service_data_values
    logger = logging_module.logging_function('logsfiles%s' %logs_file_path,file_name)
    logger.info("**********start 'main' function **********")
    try:
        configs = config_module.parse_config_obj()
        desired_site = filter(lambda x: x == nocout_site_name, configs.keys())[0]
        desired_config = configs.get(desired_site)
        site = desired_config.get('site')
        get_host_services_name(
        site_name=site,
        mongo_host=desired_config.get('host'),
        mongo_db=desired_config.get('nosql_db'),
        mongo_port=desired_config.get('port'),
	configs=configs
        )
        logger.info("**********call 'insert_bulk_perf' function for insert a record into mongodb**********" )
        insert_bulk_perf(network_data_values, service_data_values, desired_config.get('host'), desired_config.get('port'), desired_config.get('nosql_db'))
    except Exception, e:
	logger.exception('Exception: %s',str(e))
    logger.info("**********End 'Main' function**********")
