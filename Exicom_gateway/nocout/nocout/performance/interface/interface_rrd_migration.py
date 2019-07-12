from nocout_site_name import *
from logs_file_path import *
import socket,json
import imp
import time
from datetime import datetime
import imp
import os
file_name = os.path.basename(__file__)
file_name = file_name.replace(".py", "")
utility_module = imp.load_source('utility_functions', '/omd/sites/%s/nocout/utils/utility_functions.py' % nocout_site_name)
mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)
logging_module = imp.load_source('log', '/omd/sites/%s/nocout/log.py' % nocout_site_name)
logger = logging_module.logging_function('logsfiles%s' %logs_file_path,file_name)
class MKGeneralException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

def status_perf_data(site,hostlist):

	status_check_list = []
	status_service_dict = {}
	matching_criteria = {}
	configs = config_module.parse_config_obj()
	desired_site = filter(lambda x: x == site, configs.keys())[0]
        desired_config = configs.get(desired_site)
	site = desired_config.get('site')
	mongo_host=desired_config.get('host')
        mongo_db=desired_config.get('nosql_db')
        mongo_port=desired_config.get('port')
	db = mongo_module.mongo_conn(
            host=mongo_host,
            port=int(mongo_port),
            db_name=mongo_db
        )

	#db = mongo_module.mongo_db_conn(site,"nocout")
	logger.info("mongo_db_connection:%s",db)
	for host in hostlist:
		query = "GET hosts\nColumns: host_services\nFilter: host_name = %s\n" %(host[0])
		logger.info("query %s",query)
		query_output = utility_module.get_from_socket(site,query).strip()
		#print query_output,"query_output++++++++++++++++++++"
		service_list = [service_name for service_name in query_output.split(',')]
		#print service_list,"service_list___________"
		logger.info("service_list:%s",service_list)
		#print query_output
		#print service_list
		#for service_index in range(0,len(service_list)):
		#	service_list[service_index]=service_list[service_index].split(' ')[0]
		
		#print service_list
		for service in service_list:
			####updated for bhutan#######
			if service.find('_status')>0:
				status_check_list.append(service)
			#######################################	
		logger.info("status_check_list:%s",status_check_list)
		#print status_check_list,"status_check_list))))))))))))"
		for service in status_check_list:
			query_string = "GET services\nColumns: service_state service_perf_data host_address service_last_state_change\nFilter: " + \
			"service_description = %s\nFilter: host_name = %s\nOutputFormat: json\n" 	 	% (service,host[0])
			#print query_string,"query_string*******"
			logger.info("query_string:%s",query_string)
			query_output = json.loads(utility_module.get_from_socket(site,query_string).strip())
			logger.info("query_output:%s",query_output)
			#print query_output,"query_output+++++++"
			#print query_output
			try:
				if query_output[0][1]:
					perf_data_output = str(query_output[0][1])
					#print "-------------"
					#print perf_data_output,"_________"
					logger.info("perf_data_output:%s",perf_data_output)
					service_state = (query_output[0][0])
					logger.info("service_state:%s",service_state)
					#print service_state,"service_state************"
					host_ip = str(query_output[0][2])
                        		#current_time = int(time.time())
					dt = datetime.now()
					dt2 = dt.replace(second=0, microsecond=0)
					current_time = int(time.mktime(dt2.timetuple()))

					last_state_change = query_output[0][3]
                			age = current_time - last_state_change

					if service_state == 0:
						service_state = "OK"
					elif service_state == 1:
						service_state = "WARNING"
					elif service_state == 2:
						service_state = "CRITICAL"
					elif service_state == 3:
						service_state = "UNKNOWN"
                			perf_data = utility_module.get_threshold(perf_data_output)
					logger.info("perf_data: %s",perf_data)
					#print perf_data,"perf_data____"
				else:
					continue
			except:
				continue
                	for ds in perf_data.iterkeys():
                        	cur =perf_data.get(ds).get('cur')
                        	war =perf_data.get(ds).get('war')
                        	crit =perf_data.get(ds).get('cric')
				#####updated for bhutan########
				service=service.split()[0]	
				###############################
				status_service_dict = dict (sys_timestamp=current_time,check_timestamp=current_time,device_name=str(host[0]),
                                                service_name=service,current_value=cur,min_value=0,max_value=0,avg_value=0,
                                                data_source=ds,severity=service_state,site_name=site,warning_threshold=war,
                                                critical_threshold=crit,ip_address=host_ip,age=age)
				logger.info(" status_service_dict: %s",status_service_dict)
				matching_criteria.update({'device_name':str(host[0]),'service_name':service,'site_name':site,'data_source':ds})
				mongo_module.mongo_db_update(db,matching_criteria,status_service_dict,"status_services")
				logger.info("updation record in mongodb ")
                        	mongo_module.mongo_db_insert(db,status_service_dict,"status_services")
				logger.info("Insertion  record in mongodb")
				matching_criteria = {}
			#query_output = json.loads(rrd_main.get_from_socket(site,query_string).strip())
			status_service_dict = {}
		status_check_list = [] 

def status_perf_data_main():
	#logger = log_module.config_file('logsfile/performance/interface/rr_migrations/')
       #logger = log_module.config_file('logsfile/performance/interface/rr_migrations/')
        logger.info("**********start 'main' function **********")
	try:
		configs = config_module.parse_config_obj()
		logger.info('recieved configs file based on poller slave site name')
		desired_site = filter(lambda x: x == nocout_site_name, configs.keys())[0]
		desired_config = configs.get(desired_site)
		site = desired_config.get('site')
		query = "GET hosts\nColumns: host_name\nFilter: state = 0\nOutputFormat: json\n" #"GET hosts\nColumns: host_name\nOutputFormat: json\n"
		logger.info("query: %s",query)
		output = json.loads(utility_module.get_from_socket(site,query))
		#print output
		status_perf_data(site,output)
	except SyntaxError, e:
		raise MKGeneralException(("Can not get performance data: %s") % (e))
		logger.exception("Can not get performance data: %s",str(e))
	except socket.error, msg:
		raise MKGeneralException(("Failed to create socket. Error code %s Error Message %s:") % (str(msg[0]), msg[1]))
		logger.exception("Failed to create socket. Error code %s Error Message %s:",str(msg[0],msg[1]))
	except Exception, e:
		logger.exception("Error: %s",str(e))
if __name__ == '__main__':
	status_perf_data_main()	
	logger.info("**********End 'main' function **********")
		
				
