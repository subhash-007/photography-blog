"""
network_events_mongo_migration.py

File contains code for migrating the embeded mongodb data to mysql database.This File is specific to events data and only migrates the data for events

"""

from nocout_site_name import *
import mysql.connector
from datetime import datetime
from datetime import timedelta
from events_rrd_migration import get_latest_event_entry
import socket
import imp
import time
from logs_file_path import *
import os
file_name = os.path.basename(__file__)
file_name = file_name.replace(".py", "")

mongo_module = imp.load_source('mongo_functions', '/omd/sites/%s/nocout/utils/mongo_functions.py' % nocout_site_name)
utility_module = imp.load_source('utility_functions', '/omd/sites/%s/nocout/utils/utility_functions.py' % nocout_site_name)
config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)
logging_module = imp.load_source('log', '/omd/sites/%s/nocout/log.py' % nocout_site_name)
configuration_module = imp.load_source('start_bulkconfig', '/omd/sites/%s/nocout/bulkconfig/start_bulkconfig.py' % nocout_site_name)
logger = logging_module.logging_function('logsfiles%s' %logs_file_path,file_name)

def main(**configs):
    """

    Main function for the migrating the data from mongodb to mysql db.Latest record time in mysql is carried out and from latest record time to
    current time all records are migrated from mongodb to mysql.
    Args: Multiple arguments for configuration
    Kwargs: None
    Return : None
    Raise : No exception

    """
    logger.info("**********start 'main' function**********")
    data_values = []
    values_list = []
    delete_data_values =[]
    docs = []
    db = utility_module.mysql_conn(configs=configs)
    print "HERE",len(configs.get('mongo_conf'))
    #logger.info('db_detail',db)
    for i in range(len(configs.get('mongo_conf'))):
	end_time = datetime.now()
    	#start_time = get_latest_event_entry(
	#	    db_type='mysql',
	#	    db=db,
	#	    site=configs.get('mongo_conf')[i][0],
	#	    table_name=configs.get('table_name')
    	#)
	start_time = None
	print start_time,"start_time"
    	if start_time is None:
		start_time = end_time - timedelta(minutes=6)
	print "start_time",start_time
	print "end_time",end_time
    	start_time = utility_module.get_epoch_time(start_time)
    	end_time = utility_module.get_epoch_time(end_time)
  	 
	logger.info("end_time")
   	 # Read data function reads the data from mongodb and insert into mysql
    	docs = read_data(start_time, end_time,configs=configs.get('mongo_conf')[i], db_name=configs.get('nosql_db'))
	logger.info(docs)
	print int(configs.get('mongo_conf')[i][2])
        db = mongo_module.mongo_conn(
                host=configs.get('mongo_conf')[i][1],
                port=int(configs.get('mongo_conf')[i][2]),
                db_name=configs.get('nosql_db')
                )
        print db,"db"
        try :
            logger.info(db.nocout_host_event_log.find())
            db.nocout_host_event_log.drop()
        except Exception,e :
            print "Error in mongo deletion"
    	for doc in docs:
                values_list, delete_value_list = build_data(doc,configs=configs)
                data_values.extend(values_list)
		delete_data_values.extend(delete_value_list)
    if data_values:
	logger.info(data_values)
        insert_data(configs.get('table_name'), data_values, configs=configs)
        print "Data inserted into mysql db"
    else :
	print "No active event in MongoDB"
    if delete_data_values :
        delete_data('performance_eventstatus',delete_data_values, configs=configs)
	#print "Delete data",delete_data_values
    else:
        print "No delete data in the mongo db in this time frame"

def read_data(start_time, end_time, **kwargs):
    """
    Function reads the data from mongodb specific event tables for ping services and return the document
    Args: start_time(check_timestamp field in mongodb record is checked with start_time and end_time and data is extracted only
          for time interval)
    Kwargs: end_time (time till to collect the data)
    Return : document containing data for this time interval
    Raise : No exception

    """
    db = None
    port = None
    docs = []
    db = mongo_module.mongo_conn(
        host=kwargs.get('configs')[1],
        port=int(kwargs.get('configs')[2]),
        db_name=kwargs.get('db_name')
    )
    logger.info(end_time)
    logger.info(start_time)
    if db:
            cur = db.nocout_host_event_log.find({
                "check_timestamp": {"$gt": start_time, "$lt": end_time}
            })
	    for doc in cur:
            	docs.append(doc)
    logger.info(docs)
    return docs

def build_data(doc,**kwargs):
        """
	Function builds the data collected from mongodb for events according to mysql table schema and return the formatted record
	Args: doc (document fetched from the mongodb database for specific time interval)
	Kwargs: None
	Return : formatted document containing data for multiple devices
	Raise : No exception

        """
	values_list = []
	delete_values_list = []
	t = ()
	configs = config_module.parse_config_obj()
	for config, options in configs.items():
		machine_name = options.get('machine')
	#print "$$$$",doc
	if doc.get('severity') == 'DOWN' and str(doc.get('data_source')) == 'pl':
		t = (
		doc.get('device_name'),
		'Non-communicating-site',
		doc.get('sys_timestamp'),
		doc.get('check_timestamp'),
		'Non-communicating-site',
		doc.get('ip_address'),
		doc.get('max_value'),
		doc.get('avg_value'),
		#doc.get('warning_threshold'),
		#doc.get('critical_threshold'),	
		#doc.get('description'),
		'Major',
		#doc.get('site_name'),
		'Non-communicating-site',
		#doc.get('ip_address'),
		#doc.get('age'),
		'7',
		'#e87e04',
		'7'
		#machine_name
		)
                if t :
                    values_list.append(t)
	
	elif doc.get('severity') == 'UP' and str(doc.get('data_source')) == 'pl':
                t = (
                doc.get('device_name'),
                'Non-communicating-site',
                doc.get('sys_timestamp'),
                doc.get('check_timestamp'),
                'Non-communicating-site',
                doc.get('ip_address'),
                doc.get('max_value'),
                doc.get('avg_value'),
                #doc.get('warning_threshold'),
                #doc.get('critical_threshold'), 
                #doc.get('description'),
                doc.get('severity'),
                #doc.get('site_name'),
                'Non-communicating-site',
                #doc.get('ip_address'),
                #doc.get('age'),
                None,
                None,
                None
                #machine_name
                )
		#print "t", t
                if t :
		    config_dict = {}
	            delete_values_list.append(t)
		    #config_dict[(t[0],t[5], ".1.3.6.1.4.1.38016.14.4.8")] = ('INTEGER','1',"%s_manual_sync"%t[5])
		    #res = configuration_module.set_bulkconfig(config_dict)
		    #print "Manual sync response : ", res
		    #if res[0]["%s_manual_sync"%t[5]][0] == 2 :
		    #	delete_alarm_for_resync(t[0],res[0]["%s_manual_sync"%t[5]][1],configs=kwargs.get('configs'))
	t = ()
	logger.info(values_list)
	#print "values_list",values_list,"\n delete_values_list",delete_values_list
	return values_list,delete_values_list

def insert_data(table,data_values,**kwargs):
        """
	Function insert the formatted record into mysql table for multiple devices
	Args: table (mysql table on which we have to insert the data.table information is fetched from config.ini)
	Kwargs: data_values (list of formatted doc )
	Return : None
	Raise : MYSQLdb.error


        """
	print data_values,"data_values --------"
	logger.info(data_values)
	db = utility_module.mysql_conn(configs=kwargs.get('configs'))
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
	cursor = db.cursor()
    	try:
        	cursor.executemany(query, data_values)
		print "INSERTED"
  	except mysql.connector.Error as err:
        	raise mysql.connector.Error, err

    	#db.commit()
	try:
                cursor.executemany(update_query, data_values)
		#print "update_query",update_query
        except mysql.connector.Error as err:
		print "ERROR",err
                raise mysql.connector.Error, err

        db.commit()

    	cursor.close()

def delete_data(table,data_values,**kwargs):
        #print data_values,"delete_data_values --------"
        db = utility_module.mysql_conn(configs=kwargs.get('configs'))
	cursor = db.cursor()
	for data in data_values :
	    delete_query = """
                DELETE FROM performance_eventstatus
                where device_id = %s and service_name = '%s' and data_source = '%s'
                """%(data[0],data[1],data[9])
	    #print "****",delete_query
	    try :
		cursor.execute(delete_query)
	    except mysql.connector.Error as err:
		print "DELETE MySQL ERROR",err
	    db.commit()
	cursor.close()

def delete_alarm_for_resync(device_id,sync_time,**kwargs):
	print "delete_alarm_for_resync"
	#print kwargs.get('configs')
        db = utility_module.mysql_conn(configs=kwargs.get('configs'))
	#print 'db',db
        cursor = db.cursor()
        delete_query = """
                DELETE FROM performance_eventstatus
                where device_id = %s and sys_timestamp < %s and service_name !='Non-communicating-site'
                """%(device_id,sync_time)
        print "**** DELETE MySQL ALARM FOR RE-SYNC : ",delete_query,
        try :
                cursor.execute(delete_query)
        except mysql.connector.Error as err:
                print "DELETE MySQL ALARM FOR RE-SYNC ERROR",err
        db.commit()
        cursor.close()


if __name__ == '__main__':
    main()
