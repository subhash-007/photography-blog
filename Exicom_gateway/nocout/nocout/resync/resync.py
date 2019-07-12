import os
import threading
import time
import concurrent.futures
import requests
from configobj import ConfigObj
import mysql.connector
import json
from random import randint
import subprocess
import string
import re
from nocout_site_name import *
from logs_file_path import *
import imp
file_name = os.path.basename(__file__)
file_name = file_name.replace(".py", "")
config_module = imp.load_source('configparser', '/omd/sites/%s/nocout/configparser.py' % nocout_site_name)
logging_module = imp.load_source('log', '/omd/sites/%s/nocout/log.py' % nocout_site_name)
logger = logging_module.logging_function('logsfiles%s' %logs_file_path,file_name)
sys.path.insert(0, '/omd/sites/ospf1_slave_1/nocout')
from alram_clear_manual import trap_clear
config = ConfigObj("/omd/sites/%s/nocout/resync/conf.ini" % nocout_site_name)


def mysql_conn():
        '''
            Function_name : mysql_conn
            Function to create redis connection
            return: mysql connetion object
            Exception:
                   mysql Connection Exception
            parameter:None
        '''
        user_name=config.get('Database_detail','Name')
        password=config.get('Database_detail','Pass')
        db_name=config.get('Database_detail','db_name')
        port_no=config.get('Database_detail','port')
        host_name=config.get('Database_detail','host')
        
        try:
                mysql_conn = mysql.connector.connect(host=str(host_name["host"]),user=str(user_name['Name']), database=str(db_name['db_name']),password=str(password["Pass"]), port= str(port_no['port']))
        except Exception,error:
                print error
        return mysql_conn

def resync_data_process(resync_data):
    '''
	Function_name:resync_data_process
	in this method we create communicating_data and noncommunicating_data
	list of dict if device age > resend interval.
	return :valid_communicating_data in which have noncommunicating_data  
	Exception
		return:error
	parameter:resync_data:-communicating and noncommunicating device data
    '''
    try:
        communicating_data = []
        noncommunicating_data = []
        valid_communicating_data = []
        for data in resync_data:
	    if str(data["service_name"]) not in ["Non-communicating-site","Engine_ID_Mismatch"]:
            	if int(data["event_age"]) > int(int(data["resend_inerval"])*60):
		
                    if int(data["Non_communicating_status"]) == 0:
                    	communicating_data.append(data)
                    elif int(data["Non_communicating_status"]) == 1:
                    	noncommunicating_data.append(data)
            	else:
                    pass

	if communicating_data: 
		insert_data(communicating_data)
	
        logger.info("****************** communicating_data ************** %s " %(communicating_data))
        logger.info("****************** noncommunicating_data ************** %s " %(noncommunicating_data))
        for valid_data in noncommunicating_data:
            if (int(time.time()) - (valid_data["last_updated"])) > valid_data["event_age"]:
                valid_communicating_data.append(valid_data)
        logger.info("****************** valid_communicating_data ************** %s " %(valid_communicating_data))
        return valid_communicating_data
    except Exception,error:
            logger.Error("Error in resync_data_process %s " %(error))


def insert_data(data):
    '''
            Function_name : insert_data
            Function to create mysql connection and then exicute insert and delete data query
            return: None
            Exception:
                   mysql Connection Exception
            parameter:data-: data is list of dict which hold clear alarm data
    '''

    try:

	delete_query = """DELETE FROM performance_eventstatus where device_id = %s and service_name = %s"""
        insert_query = """INSERT INTO performance_performanceevent(device_id,rule_id,service_name,data_source,severity,current_value,min_value,max_value,check_timestamp,sys_timestamp,severity_colour,severity_id,event_id)\
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        insert_temp_data = """INSERT INTO xfusion_performance_alarm_status (alarm_id,device_id,user_id,description,clear_time) VALUES(%s,%s,%s,%s,%s)"""
        check_time = int(time.time())
        description_value = ('System','Resync')
        mysql_conn1 = mysql.connector.connect(host="192.168.1.55",user='root', database='xfusion_performance_spider',password="Ttpl@123", port= '3307')
        cursor = mysql_conn1.cursor()
        for insert_data in data:
            cursor.execute("SELECT * FROM performance_eventstatus WHERE device_id=%s and service_name='%s'" % (str(insert_data['device_id']),str(insert_data['service_name'])))
            event_data = cursor.fetchall()
            insert_args = (insert_data['device_id'],str(insert_data['service_name']),str(insert_data['data_source']),"CLEAR",str(insert_data['current_value']),str(insert_data['min_value']),check_time,str(insert_data['sys_timestamp']),str(insert_data['rule_id']))
            insert_history_data = trap_clear(insert_args,event_data,description_value)
            delete_args = (str(insert_data['device_id']),str(insert_data['service_name']))
            cursor.execute(insert_query,insert_history_data)
            cursor.execute(delete_query,delete_args)
            mysql_conn1.commit()
        cursor.close()
        mysql_conn1.close()
 
	    
    except Exception,error:
        logger.Error("Error in resync_data_process %s " %(error))
	


if __name__ == '__main__':
    '''
	in main method we get all communicating and noncommunicating data from 
        "exicom.vw_resynchronization_status" view. if resync status 1. Then we moddify
	some properties like(rule_id,severity,severity_colour,severity_id) 
	according to device type and then process it.else 
	return: None
	Exception:
                   reurn:error
	
    '''
    try:

        M1000_data = []
        sc_200_data = []
        exicom_rule_sc200 = {
            'rule_id' : 14,
            'severity_colour' : '#6aa84f' ,
            'severity_id' :5
            }
        exicom_rule_M1000 = {
            'rule_id' : 2,
            'severity_colour' : '#f1c40f' ,
            'severity_id' :2
            }
        cnx = mysql_conn()
        quary = """select * from  exicom.vw_resynchronization_status"""
        cursor = cnx.cursor()
	cursor.execute(quary)
        resync_data = cursor.fetchall ()       
        cursor.close()
        cnx.close()
        
	dict_keys = ('device_id','rule_id','service_name','data_source','severity','current_value','min_value','max_value','avg_value','check_timestamp','sys_timestamp','severity_colour','severity_id','model_name','resync_status','resend_inerval','last_updated','Non_communicating_status','event_age')
        for data in resync_data:
	    data = dict(zip(dict_keys,data))
            if int(data["resync_status"]) == 1:
                if data["model_name"].lower() == "m1000":
		    M1000_data.append(data)
                elif data["model_name"].lower() == "sc200":
		    sc_200_data.append(data)
            else:
                pass
		
        if M1000_data:
            insert_communicating_data = resync_data_process(M1000_data)
	    if insert_communicating_data: 
		insert_data(insert_communicating_data)

        if sc_200_data:
            insert_communicating_data = resync_data_process(sc_200_data)
	    if insert_communicating_data:
		insert_data(insert_communicating_data)

    except Exception,error:
        logger.Error("Error in data_process %s " %(error))
