import os
import sys
from configobj import ConfigObj
import mysql.connector
from nocout_site_name import *
from mysql.connector import Error as SQL_ERR

config = ConfigObj("/omd/sites/%s/nocout/conf.d/ospf1.ini" % nocout_site_name)

def mysql_conn():
    """
        Function_name : mysql_conn
        Function to create redis connection
        return: mysql connetion object
        Exception:
        mysql Connection Exception
        parameter:None
    """
    user_name = config['ospf1_slave_1']['user']
    password = config['ospf1_slave_1']['sql_passwd']
    db_name = config['ospf1_slave_1']['exicom_db']
    port_no = config['ospf1_slave_1']['mysql_port']
    host_name = config['ospf1_slave_1']['ip']

    try:
        mysql_conn = mysql.connector.connect(host=str(host_name), user=str(user_name), database=str(db_name),password=str(password), port= str(port_no))

    except Exception,error:
        print error

    return mysql_conn

def trap_clear(trap_data,alarm_status_data,description_value):

    """
	Function_name:trap_clear
	trap celar is common method which is process clear trps
	end insert data on exicom db

    """

    try:
	exicom_db_conn = mysql_conn()
        insert_query = """INSERT INTO performance_performanceevent(device_id,rule_id,service_name,data_source,severity,current_value,min_value,max_value,check_timestamp,sys_timestamp,severity_colour,severity_id,event_id)\
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
        insert_temp_data = """INSERT INTO xfusion_performance_alarm_status (alarm_id,device_id,user_id,description,clear_time) VALUES(%s,%s,%s,%s,%s)"""
        insert_temp_args = (alarm_status_data[0][0],trap_data[0],description_value[0],description_value[1],trap_data[6])
        insert_args = (trap_data[0],trap_data[8],trap_data[1],trap_data[2],"CLEAR",trap_data[4],trap_data[5],alarm_status_data[0][5],trap_data[6],alarm_status_data[0][11],alarm_status_data[0][12],alarm_status_data[0][13],alarm_status_data[0][0])
        cursor = exicom_db_conn.cursor()
        cursor.execute(insert_query,insert_args)
        cursor.execute(insert_temp_data,insert_temp_args)
        exicom_db_conn.commit()
	cursor.close()
	exicom_db_conn.close()
	return insert_args

    except SQL_ERR as e:
	print e








