#!/usr/bin/python
"""
trap_daemon.py
================

This script fetches the traps from SNMPTT DB , analyse the trap if its Open or Clear writes the formatted trap in NMS DB
traps_history_alarms : Contains all the raised and cleared traps system has received
traps_current_alarms : Contains the raised traps that are not cleared yet
traps_clear_alarms : Contains the cleared traps that haven't raised again yet

"""
from dateutil.parser import parse
from dateutil import tz
import re
from dateutil.parser import parse
import datetime
import sys, time
import os
from datetime import datetime,timedelta
from pprint import pformat
import logging
import pymongo
from pymongo import MongoClient
from mysql.connector import Connect
from mysql.connector import Error as SQL_ERR
from daemon import Daemon
from collections import OrderedDict
import mysql
from dateutil.parser import parse as date_parse
from oid_list import configured_exicom_trap_oid
from trap_alarm import alarm_id_dict
# Python list containing all the TRAP OID which are configured in the system
file_path = os.path.dirname(os.path.abspath(__file__))
logs_path = file_path+'/logs'

exicom_severity_mapping = {
0:'Info',
1:'Critical',
2:'Major',
3:'Minor',
4:'Warning',
5:'Info'
}
sc200_exicom_severity_mapping = {
1:'Critical',
2:'Major',
3:'Minor',
4:'Warning',
5:'Clear'}

exicom_rule = {
'Major' : {
        'rule_id' : 3,
        'severity_colour' : '#e87e04' ,
        'severity_id' :  3
        },
'Minor' : {
        'rule_id' : 2,
        'severity_colour' : '#f1c40f' ,
        'severity_id' :2
        },
'Clear' : {
        'rule_id' : 5,
        'severity_colour' : '#6aa84f' ,
        'severity_id' :5
        },

'Critical' : {
        'rule_id' : 4,
        'severity_colour' : '#f22613' ,
        'severity_id' :4
        },

'Warning' : {
        'rule_id' : 6,
        'severity_colour' : '#1abc9c' ,
        'severity_id' :6
        },
'Info': {
	'rule_id' : 7,
        'severity_colour' : '#3a9bdc' ,
        'severity_id' :7
	}
}
exicom_rule_sc200 =  {
'Major' : {
        'rule_id' : 11,
        'severity_colour' : '#e87e04' ,
        'severity_id' :  3
        },
'Minor' : {
        'rule_id' : 10,
        'severity_colour' : '#f1c40f' ,
        'severity_id' :2
        },
'Clear' : {
        'rule_id' : 14,
        'severity_colour' : '#6aa84f' ,
        'severity_id' :5
        },

'Critical' : {
        'rule_id' : 12,
        'severity_colour' : '#f22613' ,
        'severity_id' :4
        },

'Warning' : {
        'rule_id' : 13,
        'severity_colour' : '#1abc9c' ,
        'severity_id' :6
        },
#'Info': {
#        'rule_id' : 15,
#        'severity_colour' : '#3a9bdc' ,
#        'severity_id' :7
#        }
}

indiv_alarm_category = {'.1.3.6.1.4.1.1918.2.13.20.100':0,'.1.3.6.1.4.1.1918.2.13.20.200':0,'.1.3.6.1.4.1.1918.2.13.20.600':0\
			,'.1.3.6.1.4.1.1918.2.13.20.300':0,'.1.3.6.1.4.1.1918.2.13.20.400':0,'.1.3.6.1.4.1.1918.2.13.20.603':3,\
			'.1.3.6.1.4.1.1918.2.13.20.103':3,'.1.3.6.1.4.1.1918.2.13.20.203':3,'.1.3.6.1.4.1.1918.2.13.20.303':3,\
			'.1.3.6.1.4.1.1918.2.13.20.403':3,'.1.3.6.1.4.1.1918.2.13.20.601':1,'.1.3.6.1.4.1.1918.2.13.20.101':1,\
			'.1.3.6.1.4.1.1918.2.13.20.201':1,'.1.3.6.1.4.1.1918.2.13.20.301':1,'.1.3.6.1.4.1.1918.2.13.20.401':1,\
			'.1.3.6.1.4.1.1918.2.13.20.602':2,'.1.3.6.1.4.1.1918.2.13.20.102':2,'.1.3.6.1.4.1.1918.2.13.20.202':2,\
			'.1.3.6.1.4.1.1918.2.13.20.302':2,'.1.3.6.1.4.1.1918.2.13.20.402':2,'.1.3.6.1.4.1.1918.2.13.20.604':4,\
			'.1.3.6.1.4.1.1918.2.13.20.104':4,'.1.3.6.1.4.1.1918.2.13.20.204':4,'.1.3.6.1.4.1.1918.2.13.20.304':4,\
			'.1.3.6.1.4.1.1918.2.13.20.404':4}
indiv_clear_alarm = ['.1.3.6.1.4.1.1918.2.13.20.400','.1.3.6.1.4.1.1918.2.13.20.401','.1.3.6.1.4.1.1918.2.13.20.402',\
			'.1.3.6.1.4.1.1918.2.13.20.403','.1.3.6.1.4.1.1918.2.13.20.404']

# Python Dictionary containing indexes of each required parameter to be extracted from FORMATLINE colunm of SNMPTT in name:index key-value pair
formatline_indexes = {
        # for ceragon
        'format_indexes': {
            'event_name': 0,
            'event_no': 1,
            'severity': 2,
            'slot_id': 3,
            'interface_id': 4,
	    'module': 5,
	    'description' : 6,
	    'event_time' : 8,
	    'ne_id' : 9,
	    'alarm_class' : 10,
	    'probable_cause' : 11,
	    'vanu_id' : 3
	    # 'trap_event_traffic_desc' : 11,
            } }

# determines a trap uniquely, for a device type
unique_key_indexes = {
        # (ip, eventno, slot_id) for ceragon
        'exicom' : OrderedDict(
                [('device_id', 0), ('service_name', 1)])
        }


class Logger:
    """
    A generic logger class, returns a logger object.
    """

    def __init__(self, name = 'trap_handler', logfile_path = logs_path, logger=None):
        """
        Function name : __init__()     
                        Initialize the logfile name, path and logger object

        Args : self (reference to the object of class MyDBConnection), logfile_path (path where log file is to be made),name (name of the log file)

        Returns : None

        Exception : None
        """
        self.name = name
        #self.logfile = logfile
	self.logfile_path = logfile_path
        self.logger = logger

    def get(self):
        """
        Function name : get()
                        Returns a logger object, which logs activities to a
                        log file
        Args : self (reference to the object of class Logger)

        Return : logger object

        Exception : Exception (write to log)
        """
	try:
        	self.logger = logging.getLogger(self.name)
        	#if not len(self.logger.handlers):
                self.logger.setLevel(logging.DEBUG)
                handler=logging.FileHandler(os.path.join(self.logfile_path, self.name + datetime.now().strftime("_%Y%m%d.log")))
                formatter = logging.Formatter('%(asctime)s - %(levelname)s >> %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
		return self.logger

        except Exception as exp:
            print "Unable to locate log file...logging to stdout"
            print exp


class MyDaemon(Daemon):
    """
    Daemon class that provides definition for run() function
    """
    def run(self):
        """
        Function name : run()
                        Reads all the device IP and device name configured in NMS DB (device_device table)
                        If devices are found, call process_history_alarms() that import all the traps into history trap table after fomating it
                        If trap data are found, call process_current_clear_alarms() that analyses the trap data and writes the cleared trap in clear trap table
                        and raised trap in current trap table
                        Also write the exception/error in the log file

        Args : self (reference to the object of class MyDaemon)

        Returns : None

        Exception : None
        """
        logger_instance = Logger()
        logger = logger_instance.get()
	#print logger
        logger.debug('Trap daemon started at: %s' % pformat(datetime.now()))

        devices_info = []
        processed_traps = []
        # get device names from device_device table in configuration db
        # need to keep the device names in memory
        conf_db_obj = MyDBConnection(conf='%s/trap_conf.py' % file_path, db_type='conf_db')
        conf_db = conf_db_obj.get_connection()
        #logger.debug('Got db connection : %s' % pformat(conf_db))
        if conf_db:
            device_qry = "SELECT device_id, ipaddress FROM device_device"
            cursor = conf_db.cursor()
            cursor.execute(device_qry)
            devices_info = cursor.fetchall()
        conf_db_obj.close_connection()
        if devices_info:
            processed_traps,escalation,mat_db_obj = process_history_alarms(devices_info)
        if processed_traps:
	    #print processed_traps
	    process_current_alarms(processed_traps,escalation,mat_db_obj)
            #process_current_clear_alarms(processed_traps)
	    logger.debug('Processed %s traps\n' % len(processed_traps))
        logger.debug('Done Processing %s ...\n' %(datetime.now()))
        print 'Processed %s traps\n' % len(processed_traps)
        print 'Done Processing ...\n'
	print  "end:",datetime.now(),"\n"

class MyDBConnection:
    """
    Database connection class
    """
    def __init__(self, conf=None, db_type=None):
        """
        Function name : __init__()     
                        If conf file path is passed , read the file and write its content to conf_vars dictionary.
                        Update conf_vars dictionary for specified db_type

        Args : self (reference to the object of class MyDBConnection), conf (path to config file of DB),db_type (DB type name defined in config file)

        Returns : None

        Exception : None
        """
        self.conf_vars = {}
        self.db = None
        if conf:
            execfile(conf, self.conf_vars)
            self.conf_vars = self.conf_vars[db_type]
            #del self.conf_vars['__builtins__']

    def get_connection(self):
        """
        Function name : get_connection()
                        Return DB object of specified DB reading parameters from conf_vars dictionary

        Args : self (reference to the object of class MyDBConnection)

        Returns : DB object

        Exception : SQL_ERR (write to log)
                    Exception (write to log)
        """

        try:
            self.db = Connect(host=self.conf_vars['host'], port=self.conf_vars['port'], 
                    user=self.conf_vars['user'], password=self.conf_vars['password'], 
                    database=self.conf_vars['database'])
        except SQL_ERR as e:
	    logger.exception('Exception: %s',str(e))
            print e
        except Exception as exp:
	    logger.exception('Exception: %s',str(exp))
            print exp
            
        return self.db

    def close_connection(self):
        """
        Function name : close_connection()
                        Closes the MySQL DB connection
                        
        Args : self (reference to the object of class MyDBConnection)

        Returns : None

        Exception : None
        """
        if isinstance(self.db, mysql.connector.connection.MySQLConnection):
            self.db.close()
def mongo_conn(conf=None, db_type=None) :
    """
    
        Function_name : mongo_conn (function for making 
        mongo db connection) 
        return: db
        Exception:
               PyMongoError
    
    """
    conf_vars = {}
    db = None
    if conf:
        execfile(conf, conf_vars)
        conf_vars = conf_vars[db_type]
    host = conf_vars['host']
    port = conf_vars['port']
    try:
        client = MongoClient(host, int(port))
        #mongodb = client.aralm_escalation
    except pymongo.errors.PyMongoError, e:
        raise pymongo.errors.PyMongoError, e
    return client


def process_history_alarms(devices_info):
    """
    Function name : process_history_alarms()
                    Reads the index of last processed data from SNMPTT DB id_info table
                    If index is returned , read the trap data from SNMPTT table having index greater than index of last processed data
                severity    Update the index of last processed data with the last index of fetched trap data and current processed time in SNMPTT DB id_info table
                    If trap data is available, normalize the trap data acording to required format
                    Create DB connectionand insert the normalized trap data into history trap table
                    Logs the Exception/Error in the log file
                    Return trap data

    Args : devices_info (list of Device name and Device IP Address)

    Returns : trap_data (list of traps)

    Exception : SQL_ERR(write to log)
                Exception(write to log)
    """
    trap_data = []
    index = ()
    exicom_config_oid =[]
    escalation =[]
    mat_db_obj=''
    # Connection to snmptt database
    trap_db_obj = MyDBConnection(conf='%s/trap_conf.py' % file_path, db_type='snmptt')
    trap_db = trap_db_obj.get_connection()
    index_query = "SELECT processed_row FROM id_info"
    try:
        cursor = trap_db.cursor()
        cursor.execute(index_query)
        index = cursor.fetchall()
    except SQL_ERR as e:
	logger.exception('Exception: %s',str(e))
        print 'DB error with id_info'
        print e
    except Exception as exp:
	logger.exception('Exception: %s',str(exp))
        print 'Exception with id_info'
        print exp
    if len(index):
	last_index = index[0][0]
	#index[0] = 74838
        select_trap_qry = "SELECT id, eventname, eventid,hostname, trapoid, category, \
                severity, uptime, traptime, formatline FROM"
        select_trap_qry += " snmptt WHERE id > %s" % index[0]
	try:
	    cursor.execute(select_trap_qry)
	    trap_data = cursor.fetchall()
	    #print "TRAP DATA " ,trap_data
	except SQL_ERR as e:
	    logger.exception('Exception: %s',str(e))
	    print 'DB error with snmptt'
	    print e
	except Exception as exp:
	    logger.exception('Exception: %s',str(exp))
	    print 'Exception with snmptt'
	    print exp
        logger.debug("Processed data : %s \n" % str(trap_data))
	#logger.debug("Processed Row Index : %s \n" % str(trap_data[-1][0]))
        if len(trap_data):
	    logger.debug("Processed Row Index : %s \n" % str(trap_data[-1][0]))
            update_index = trap_data[-1][0]
            update_index_qry = "UPDATE id_info SET processed_row=%s, timestamp='%s', `by` = '%s'" \
                    % (update_index, datetime.now(), "Subhash")
	    print update_index_qry
            cursor.execute(update_index_qry)
            trap_db.commit()
    else:
        index_query = "INSERT INTO id_info(processed_row, timestamp,`by`) "
	index_query += "VALUES (%s, '%s','subhash')" % (0, datetime.now())
	print "index_query",index_query
        try:
	    cursor.execute(index_query)
	    trap_db.commit()
        except SQL_ERR as e:
	    logger.exception('Exception: %s',str(e))
	    print 'DB error with insert id_info'
	    print e
        except Exception as exp:
	    logger.exception('Exception: %s',str(exp))
	    print 'Exception with insert id_info'
	    print exp
    trap_db_obj.close_connection()
    trap_db.close()
    if len(trap_data):
	trap_data,escalation,mat_db_obj = normalize_trap_data(trap_data, devices_info)
	logger.info("trap_data %s" %trap_data)	
        # bulk insert processed traps into final tables
    return trap_data,escalation,mat_db_obj


def process_current_alarms(trap_data,escalation,mat_db_obj):
    """
    Function name : process_current_clear_alarms()
                        Create DB connection object by reading connection parameters from the specified config file for specified DB
                        For each trap data record :
                                If 'ceragon' present in eventname name column of trap data read the indexes of unique keys from dictionary unique_key_indexes
                                If trap severity is clear set query to delete the trap from current trap table and insert into clear alarm table
                                If trap severity is not clear set query to delete the trap from clear trap table and insert into current alarm table
                                If indexes of unique keys are found,bind the unique key name and its value from trap data in key-value pair
                                If DB object exists, execute the delete query
                                Check if the row to be inserted is already present in DB table
                                If not present, execute the insert query
                        Close DB connection

    Args : trap_data (list of traps)

    Returns : None

    Exception : SQL_ERR(write to log)
                Exception(write to log)
    """
    #print "TRAP_DATA : %s",trap_data
    global unique_key_indexes
    flag = 0
    exicom_db_obj = MyDBConnection(conf='%s/trap_conf.py' % file_path, db_type='mat_db')
    exicom_db = exicom_db_obj.get_connection()
    db_obj = MyDBConnection(conf='%s/trap_conf.py' % file_path, 
		db_type='processed_traps')
    db = db_obj.get_connection()
    insert_into ='performance_eventstatus'
    logger.info("trap_data===========%s"%trap_data)
    for data in trap_data:
	flag = 0
        indexes = None
        # load unique indexes
	indexes = unique_key_indexes['exicom']

        if 'clear' in data[3].lower():
            delete_from = 'performance_eventstatus'
        #else:
        #    insert_into = 'performance_eventstatus'
        if indexes:
            keys, vals = indexes.keys(), indexes.values()
	    vals = map(lambda e: data[e], vals)
	    insert_qry = "INSERT INTO %s" % insert_into
            insert_qry += (
                    "( device_id,service_name,data_source,severity,current_value,min_value,check_timestamp,sys_timestamp, rule_id,severity_colour,severity_id )" 
                    "VALUES (%s, %s, %s,%s, %s, %s,%s, %s,%s,%s, %s)"
                    )
	    if data[3].lower() =='clear':
		delete_qry = "DELETE FROM %s WHERE " % delete_from
            	delete_qry += ' AND '.join("%s='%s'" % t for t in zip(keys, vals))
		flag =1
	    else:
	    	update_qry = "UPDATE %s set current_value='%s' , check_timestamp = '%s' ,severity = '%s',rule_id = '%s',severity_colour = '%s',severity_id= '%s' WHERE " %(insert_into,data[4],data[6],data[3],data[8],data[9],data[10])

	        update_qry += ' AND '.join("%s='%s'" % t for t in zip(keys, vals))
	   
	        #print "\nUpdate query : ", update_qry, "\n ^^^^^"
            find_existing_qry = "SELECT COUNT(1) FROM %s WHERE " % insert_into
            find_existing_qry += ' AND '.join("%s='%s'" % t for t in zip(keys, vals))
	    #(1, 'rectifierCommsLost', 'Rectifier Comms Lost', 'Minor', 'Rectifier Comms Lost', '192.168.10.55', 1546502937, 1546502937, 10, '#f1c40f', 2)
	    insert_history ="""INSERT INTO performance_performanceevent( device_id,service_name,data_source,severity, current_value,min_value,check_timestamp,sys_timestamp, rule_id,severity_colour,severity_id )
         VALUES (%s, %s, %s,%s, %s, %s,%s, %s,%s,%s,%s)"""
            if db:
                try:
                    cursor = db.cursor()
                    db.commit()
                    cursor.execute(find_existing_qry)
                    trap_exists = cursor.fetchall()

                    if not trap_exists[0][0] and flag == 0:
                        cursor.execute(insert_qry,data)
                        cursor.execute(insert_history,data)

                        db.commit()
                    elif flag ==1:
                        #cursor.execute("SELECT id,sys_timestamp FROM performance_eventstatus WHERE device_id=%s and service_name='%s'" % (data[0],data[1]))
                        cursor.execute("SELECT * FROM performance_eventstatus WHERE device_id=%s and service_name='%s'" % (data[0],data[1]))
                        event_id = cursor.fetchall()

                        insert_query = """INSERT INTO performance_performanceevent(device_id,rule_id,service_name,data_source,severity,current_value,min_value,max_value,check_timestamp,sys_timestamp,severity_colour,severity_id,event_id)\
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                        if event_id:
                            try:
			        data1 = (data[0],data[8],data[1],data[2],"CLEAR",data[4],data[5],data[6],event_id[0][1],data[9],data[10],event_id[0][0])
			        print data1,"insert********************"
			        #trap_clear(data,exicom_db,event_id)
				logger.info("trap_clear_insert query %s on %s time" %(insert_query,int(time.time())))
			        cursor.execute(insert_query,data1)
                                cursor.execute(delete_qry)
                                db.commit()
				trap_clear(data,exicom_db,event_id)
                            except SQL_ERR as e:
                                logger.exception('Exception in spider node insert and delete : %s',str(e))

                        else:
                            insert_query = """INSERT INTO performance_performanceevent(device_id,rule_id,service_name,data_source,severity,current_value,min_value,check_timestamp,sys_timestamp,severity_colour,severity_id)\
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                            data1 = (data[0],data[8],data[1],data[2],"CLEAR",data[4],data[5],data[6],data[7],data[9],data[10])
                            print insert_query,data1,"when trap is cleard"
                            cursor.execute(insert_query,data1)
                            db.commit()
                    else :
                        print "update_data******************88",data,insert_history
                        cursor.execute(insert_history,data)
                        print "update query : ",update_qry, "\n -----------------------"
                        cursor.execute(update_qry)
                        db.commit()

		    
                except SQL_ERR as e:
		    logger.exception('Exception: %s',str(e))
                    print 'DB error in current/clear...',e
                except Exception as exp:
		    logger.exception('Exception: %s',str(exp))
                    print 'Exception in current/clear...',exp
    db_obj.close_connection()
    exicom_db_obj.close_connection()
    exicom_db.close()
    if escalation:
	mat_db = mat_db_obj.get_connection()
        for data in escalation:
	    if data[6].lower() == 'clear':
		is_close = 1
	        update_query = """INSERT INTO `escalation_level_status`\
 	        (`mat_id`, `ticket_id`, `last_escalation_level`, `current_escalation_level`, \
                `creation_date`, `last_modified`, `is_close`) \
                 VALUES ('%s','%s','%s','%s',%s,%s,'%s')\
                 ON DUPLICATE KEY UPDATE `last_modified` = '%s' , `is_close` ='%s' """ \
		%(data[0],data[1],data[2],data[3],data[4],data[5],is_close,data[4],is_close);
	  
	    else:
		is_close = 0
		update_query = """INSERT INTO `escalation_level_status` (`mat_id`, `ticket_id`, `last_escalation_level`,\
		`current_escalation_level`, `creation_date`, `last_modified`, `is_close`)\
		VALUES ('%s','%s','%s','%s',%s,%s,'%s') ON DUPLICATE KEY UPDATE `ticket_id`='%s'""" \
		%(str(data[0]),str(data[1]),str(data[2]),str(data[3]),str(data[4]),str(data[5]),is_close,str(data[1]))

	    cursor = mat_db.cursor()
	    cursor.execute(update_query)
	    mat_db.commit()
    mat_db_obj.close_connection()
   	    
def trap_clear(trap_data,exicom_db_conn,alarm_id):
    try:
	#exicom_db_obj = MyDBConnection(conf='%s/trap_conf.py' % file_path, db_type='exicom')
        #exicom_db = exicom_db_obj.get_connection()

	print trap_data,exicom_db_conn
	print "In trap_clear : ",alarm_id
        insert_query = """INSERT INTO performance_performanceevent(device_id,rule_id,service_name,data_source,severity,current_value,min_value,check_timestamp,sys_timestamp,severity_colour,severity_id,event_id)\
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        insert_temp_data = """INSERT INTO xfusion_performance_alarm_status (alarm_id,device_id,user_id,description,clear_time) VALUES(%s,%s,%s,%s,%s)"""
	#(2, 'noBattery3', 'noBattery3', 'Clear', 'Batt3 Not Present', '192.168.10.53', 1544689543, 1544689176, 5, '#6aa84f', 5)
	#(1, 14, 'lvdFail', 'Digital Input 52', 'Clear', 'LVD Fail', 'CLEAR', 1545281835, 1545213780, '#6aa84f', 5, 156)
	insert_temp_args = (alarm_id[0][0],trap_data[0],'System','Auto Clear',trap_data[6])
	insert_args = (trap_data[0],trap_data[8],trap_data[1],trap_data[2],"CLEAR",trap_data[4],trap_data[5],trap_data[6],alarm_id[0][1],trap_data[9],trap_data[10],alarm_id[0][0])
	print "insert_temp&&&&&&&&&&&&insert_query",insert_query,insert_args
	logger.info(insert_query)
	logger.info(insert_temp_data)
	cursor = exicom_db_conn.cursor()
	cursor.execute(insert_query,insert_args)
	cursor.execute(insert_temp_data,insert_temp_args)
        exicom_db_conn.commit()	
    except SQL_ERR as e:
        logger.exception('Exception: %s',str(e))

def normalize_trap_data(data, devices_info):
    """
    Function name : normalize_trap_data()
                    Formats the data for processed alarm tables.
                    
    Args : data (list of traps) ,devices_info (list of Device name and Device IP Address)

    Returns : None

    Exception : Exception(write to log)
    """
    try :
	global rule
	global exicom_rule
	global exicom_rule_sc200
        global formatline_indexes
	global exicom_severity_mapping	
	global sc200_exicom_severity_mapping
	service =None
	service_name_dict = alarm_id_dict()
        out = []
	mat_indiv_oid_list = []
	mat_m1000_oid_list =[]
	escalation =[]
	rule = 0
	mat_db_obj = MyDBConnection(conf='%s/trap_conf.py' % file_path,
                db_type='mat_db')
        mat_db = mat_db_obj.get_connection()
	m1000_matdata_query = "select id,oid,alarm_name,severity from mat_table where model_name in ('M1000','M2000') and is_active = 1"
	indiv_matdata_query = "select id,oid,alarm_name,severity,alarm_index,alarm_category from mat_table \
	where model_name = 'SC200' and is_active = 1 and alarm_type IS NULL"
	global_matdata_query = "select id,oid,alarm_name,severity,alarm_index,alarm_category from mat_table\
	 where model_name = 'SC200' and  is_active = 1 and alarm_type = 1"
        try:
	    indiv_cursor = mat_db.cursor(buffered=True)
	    global_cursor = mat_db.cursor(buffered=True)
	    m1000_cursor = mat_db.cursor()
            indiv_cursor.execute(indiv_matdata_query)
	    global_cursor.execute(global_matdata_query)
	    m1000_cursor.execute(m1000_matdata_query)
            indiv_matdata = indiv_cursor.fetchall()
	    global_matdata = global_cursor.fetchall()
	    m1000_matadata = m1000_cursor.fetchall()
        except SQL_ERR as e:
            logger.exception('Exception: %s',str(e))
            print 'NO Data in MAT'
            print e
        except Exception as exp:
            logger.exception('Exception: %s',str(exp))
            print 'Exception with MAT',str(exp)
	mat_db_obj.close_connection()
	client = mongo_conn(conf='%s/trap_conf.py' % file_path,db_type='mongo_db')
	mongodb = client.aralm_escalation
	print (mongodb)
	for mat_data in m1000_matadata:
		mat_m1000_oid_list.append(mat_data[1])
	for mat_data in indiv_matdata:
		mat_indiv_oid_list.append(mat_data[1])
        for entry in data:
            formatline = entry[-1]
            indexes = formatline_indexes['format_indexes']
            for d in devices_info:
                current_device = None
		if "UDP/IPv6" in str(entry[3]):
		    entry_host = entry[3].split('[')[1].split(']')[0]
	            if (str(entry_host) == str(d[1])):
                        current_device = d[0]
			entry = list(entry)
			entry[3]= entry_host
			entry = tuple(entry)
                        break
		else:
	            if (str(entry[3]) == str(d[1])): 
        	        current_device = d[0]
		        print "current_device******************",current_device
        	        break
            oid = str(entry[4]).strip()
	    if oid in configured_exicom_trap_oid :
		try :
                    trap_time = date_parse(str(entry[8]))
                    event_time = time.mktime(trap_time.timetuple())
                except Exception,exp :
                    event_time = ''
		if oid in mat_m1000_oid_list:
		    for oid_list in m1000_matadata:
			if oid == oid_list[1]:			    
			    if int(entry[9].split('|')[-3]) == 1 :
				severity = oid_list[3]
				if  severity == 'None':
				    severity = exicom_severity_mapping[int(entry[9].split('|')[-2])]				
			    else:
				print "Issue in clear"
				severity = 'Clear' 			   
			    #check_severity = exicom_severity_mapping[int(entry[9].split('|')[-2])]
                            #if check_severity.lower() in 'clear':
                            #    severity = check_severity
                            #else:
                            #    severity = oid_list[3]
                            #    if  severity == 'None':
                            #        severity = exicom_severity_mapping[int(entry[9].split('|')[-2])]
                            datasouce = oid_list[2]
                            service = str(entry[9]).split('|')[0]
                            current_value = entry[9].split('|')[-4]
                            timestamp = str(entry[9]).split('|')[-1].rstrip()
			    try :
				check_timestamp = int(time.mktime(time.strptime(timestamp,"%d/%m/%Y %H:%M:%S")))-19800
			    except Exception,e:
				check_timestamp = int(time.mktime(time.strptime(timestamp,"%d/%m/%y-%H:%M:%S")))-19800
                            ticket_id = oid_list[1]+'_'+ str(current_device) + '_' + str(oid_list[0])
			    rule = 0
                            out,escalation = alarm_details(oid_list[0],ticket_id,check_timestamp,severity,current_device,service,\
                            datasouce,current_value,str(entry[3]),event_time,escalation,out,rule)
		elif oid in mat_indiv_oid_list:
		    alarm_index = int(entry[9].split('|')[1])
		    for oid_list in indiv_matdata:
		        if oid  == str(oid_list[1]) and alarm_index  == int(oid_list[4]):
			    check_severity = entry[6]
			    if check_severity.lower() in 'clear':
				severity = check_severity
			    else:
		            	severity = oid_list[3]
			        if  severity == 'None':
			            severity = check_severity
			    datasouce = oid_list[2]
			    alarm_index = int(entry[9].split('|')[1])
			    alarm_cat = indiv_alarm_category[str(oid)]			    
			    service = service_name_dict[alarm_cat][alarm_index]
			    current_value = entry[9].split('|')[2]
                            check_timestamp = event_time
			    ticket_id = oid_list[1]+'_'+ str(current_device) + '_'+ str(oid_list[0])
			    cursor = mongodb.escalation.find({str(current_device)+'_'+service: {"$exists": True}})
			    rule = 1
			    if cursor.count() > 0:
				for val in cursor:
				    mongodb.escalation.update({str(current_device)+'_'+service:val.values()},\
				    {'$set':{str(current_device)+'_'+service:ticket_id+'_'+datasouce}})
			    else:
			    	record_id = mongodb.escalation.insert({str(current_device)+'_'+service:ticket_id+'_'+datasouce})
			    out,escalation = alarm_details(oid_list[0],ticket_id,check_timestamp,severity,current_device,service,\
			    datasouce,current_value,str(entry[3]),event_time,escalation,out,rule)
			    #print out
		        else:
			   pass
		elif oid == '.1.3.6.1.4.1.1918.2.13.20.700':
		    for oid_list in global_matdata:
                         alarm_index = int(entry[9].split('|')[1])
                         alarm_cat = int(entry[9].split('|')[2])
			 #print "alarm_cat :",alarm_cat
			 rule =1
			 #print "OID LIST 4 :",oid_list
			 #print alarm_cat,oid_list,"888888888888888888888"
                         try:
                            if  int(oid_list[4]) == alarm_index and  int(oid_list[5]) == alarm_cat:  #int(oid_list[5]) == alarm_cat: #int(oid_list[4]) == alarm_index
				print oid_list[5],alarm_cat,"alarm_cat"	
                                service = service_name_dict[alarm_cat][alarm_index]
				print service,"service============"
                                datasouce = str(oid_list[2])
				print datasouce,"ddddddddddddddd"
                                current_value = str(entry[9].split('|')[3])
                                check_severity = str(sc200_exicom_severity_mapping[int(entry[9].split('|')[4])])
                                check_timestamp = event_time
                                if check_severity.lower() in 'clear':
                                    severity = check_severity.title()
                                else:
                                    severity = oid_list[3]
                                    if  severity == 'None':
                                        severity = str(sc200_exicom_severity_mapping[int(entry[9].split('|')[4])]).title()
				ticket_id = oid_list[1]+'_'+ str(current_device)+ '_'+ str(oid_list[0])
				out,escalation = alarm_details(oid_list[0],ticket_id,check_timestamp,severity,current_device,\
				service,datasouce,current_value,str(entry[3]),event_time,escalation,out,rule)
                         except Exception as exp:
                                print exp
	        elif oid in indiv_clear_alarm:
		    alarm_index = int(entry[9].split('|')[1])
                    alarm_cat = indiv_alarm_category[oid]
                    service = service_name_dict[alarm_cat][alarm_index]
		    current_value = entry[9].split('|')[2]
		    severity = str(entry[6])
		    check_timestamp = event_time
		    cursor = mongodb.escalation.find({str(current_device)+'_'+service: {"$exists": True}})
		    rule = 1
		    for val in cursor:		
		        ticket_value = val.values()
		       	ticket_ds = ticket_value[1]
			oid_val = ticket_ds.split('_')[0]
		        mat_id = int(ticket_ds.split('_')[-2])
			datasouce = str(ticket_ds.split('_')[-1])
			ticket_id = oid_val + '_' + ticket_ds.split('_')[1] + '_' + str(mat_id)
			mongodb.escalation.remove({str(current_device)+'_'+service:ticket_value[1]})
			out,escalation = alarm_details(mat_id,ticket_id,check_timestamp,severity,current_device,\
                                service,datasouce,current_value,str(entry[3]),event_time,escalation,out,rule)
		else:
		    pass
            else :
                logger.error('TRAP OID %s NOT MAPPED IN CONFIG/ REPEATED COUNTER ID',str(entry[4]).strip())
	client.close()
        #print out,escalation,mat_db_obj        
	
    except Exception as exp:
        logger.exception('Exception in normalize_trap_data: %s',str(exp))
        print 'Exception in normalize_trap_data...',exp
    print out,escalation,mat_db_obj
    return out,escalation,mat_db_obj
	
def alarm_details(mat_id,ticket_id,check_timestamp,severity,current_device,service,datasouce,current_value,oid,event_time,escalation,out,rule):
    if rule ==  0:
        last_escalation_level=0
        current_escalation_level=0
        notification_list =(mat_id,ticket_id,last_escalation_level,current_escalation_level,\
        check_timestamp,check_timestamp,severity)
        escalation.append(notification_list)
        processed_entry = (current_device,  service, str(datasouce),
        str(severity),str(current_value),str(oid),int(event_time),\
        int(check_timestamp),exicom_rule[severity]['rule_id'],\
        exicom_rule[severity]['severity_colour'],exicom_rule[severity]['severity_id'])
        out.append(processed_entry)
    else:
	severity = severity.title()
	#print severity,"severity============"
	last_escalation_level=0
        current_escalation_level=0
        notification_list =(mat_id,ticket_id,last_escalation_level,current_escalation_level,\
        check_timestamp,check_timestamp,severity)
        escalation.append(notification_list)
        processed_entry = (current_device,  service, str(datasouce),
        str(severity),str(current_value),str(oid),int(event_time),\
        int(check_timestamp),exicom_rule_sc200[severity]['rule_id'],\
        exicom_rule_sc200[severity]['severity_colour'],exicom_rule_sc200[severity]['severity_id'])
        out.append(processed_entry)
    return out,escalation

if __name__ == "__main__":
    """
    Create a logger object
    Calls the appropriate method of Daemon class as passed in argument
    """
    daemon = MyDaemon('/tmp/trap_handler.pid', 'trapHandler')
    print  "start:",datetime.now(),"\n"
    logger_instance = Logger()
    logger = logger_instance.get()
    logger.debug('Processing Started at: %s' % pformat(datetime.now()))
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        elif 'status' == sys.argv[1]:
            daemon.status()
        elif 'foreground' == sys.argv[1]:
            daemon.run()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
    print  "end:",datetime.now(),"\n"
