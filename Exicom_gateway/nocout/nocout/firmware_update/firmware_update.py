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

config = ConfigObj("/omd/sites/%s/nocout/firmware_update/conf.ini" % nocout_site_name)


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
		data = res["object"]
		#print data
		#return data
	except IOError,e:
		print "error in Auth",e
	return data


def check_network(valid_data):
	try:
		valid_network = []
		invalid_network = []
		print valid_data["device_ip"]
		response = os.system("ping -c 5 -w 5 "+ valid_data["device_ip"])
		if response == 0:

			if 'ping_status_before' not in valid_data:
				valid_data['ping_status_before'] = 'up'
			else:
				valid_data['ping_status_after'] = 'up'
			valid_network.append(valid_data)
		else:
			if 'ping_status_before' not in valid_data:
				valid_data['ping_status_before'] = 'down'
			
			else:	
				valid_data['ping_status_after'] = 'down'
			invalid_network.append(valid_data)


		if invalid_network:
			insert_data(invalid_network)
	
	except IOError,e:
		print "error in Auth",e
	return valid_network




def get_schedule_firmware_list(data):	
	try:				
		if data:
		
			black_list_data = []
			white_list_data = []
			ping_data = check_network(data)
		
			before_firmware_version = get_firmware_version(ping_data)
			print before_firmware_version[0]['type']	
			if  before_firmware_version[0]['type'] in ['icp']:
				#print "before_firmware_version",before_firmware_version
				if before_firmware_version[0]['blacklist'] != None: 	
					get_invalid_version = get_valid_firmware(before_firmware_version[0]['blacklist'].split(','),before_firmware_version[0]["polled_sw_version_before"])
					get_valid_version = get_valid_firmware(before_firmware_version[0]['whitelist'].split(','),before_firmware_version[0]["polled_sw_version_before"])
					print get_invalid_version ,"  get_invalid_version  ","get_valid_version   ",get_valid_version	
			
					logger.info("black_list %s and white_list %s data" %(get_invalid_version,get_valid_version))
					if get_invalid_version:
						print "black_listed"
						logger.info('invalid_data %s ' %(get_invalid_version))
						before_firmware_version[0]["black_list_bit"] == 1
	                        		insert_data(before_firmware_version)
			 		else:
						if get_valid_version:
							#if before_firmware_version[0]['firmware_protocol'] == 'http':			
							update_firmware_data =  update_firmware(before_firmware_version)
							#update_firmware_data[0]['black_list_bit'] = 0
							logger.info("updated firmware data   %s" %(update_firmware_data))
							time.sleep(125)
							ping_data1 = check_network(update_firmware_data)	
							final_list = get_firmware_version(ping_data1)
							#final_list[0]['black_list_bit'] = 0
							insert_data(final_list)
							#else:
							#	logger.info("HTTPS for M100 : INVALID : %s" %before_firmware_version)
							#	ping_data1 = check_network(before_firmware_version)
							#	insert_data(ping_data1)
				       		else:
							logger.info("both_condition fail %s " %(before_firmware_version))
							before_firmware_version[0]["black_list_bit"] = 1 
							insert_data(before_firmware_version)
				else:
					print "%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%" 
					update_firmware_data =  update_firmware(before_firmware_version)
					print "update_firmware_data", update_firmware_data
                                        logger.info("updated firmware data   %s" %(update_firmware_data))
                                        time.sleep(125)
                                        ping_data1 = check_network(update_firmware_data)
                                        final_list = get_firmware_version(ping_data1)
                                        insert_data(final_list)

			elif before_firmware_version[0]['type'] in ['frm']:
				get_invalid_version = get_valid_firmware(before_firmware_version[0]['blacklist'].split(','),before_firmware_version[0]["polled_sw_version_before"])
                                get_valid_version = get_valid_firmware(before_firmware_version[0]['whitelist'].split(','),before_firmware_version[0]["polled_sw_version_before"])
                                print get_invalid_version ,"  get_invalid_version  ","get_valid_version   ",get_valid_version   
                        
                                logger.info("black_list %s and white_list %s data" %(get_invalid_version,get_valid_version))
                                if get_invalid_version:
                                        print "black_listed"
                                        logger.info('invalid_data %s ' %(get_invalid_version))
					before_firmware_version[0]["black_list_bit"] = 1
                                        insert_data(before_firmware_version)
                                else:
                                        if get_valid_version:
                                                if before_firmware_version[0]['firmware_protocol'] == 'http':
                                                	update_firmware_data =  update_firmware(before_firmware_version)
                                                	logger.info("updated firmware data   %s" %(update_firmware_data))
                                                	time.sleep(60)
                                                	ping_data1 = check_network(update_firmware_data)
                                                	final_list = get_firmware_version(ping_data1)
							#final_list[0]['black_list_bit'] = 0
                                                	insert_data(final_list)
						else:
                                                        logger.info("HTTPS for M100 : INVALID : %s" %before_firmware_version)
							before_firmware_version[0]['black_list_bit'] = 0
							before_firmware_version[0]['invalid_protocol']=1
                                                        ping_data1 = check_network(before_firmware_version[0])
							ping_data1[0]["ping_status_before"]= 'up'
                                                        insert_data(ping_data1)
                                        else:
                                                logger.info("both_condition fail %s " %(before_firmware_version))
						before_firmware_version[0]["black_list_bit"] = 1
                                                insert_data(before_firmware_version)
						
						
			else:
				data_config_file = update_firmware(before_firmware_version)
				ping_data1 = check_network(update_firmware_data)
				insert_config(data_config_file)

	except IOError,e:
		logger.exception("Error %s", str(e))


def get_valid_firmware(firmware_version,polled_sw_version_before):
    try:
    	    if len(polled_sw_version_before.split('.')) == 2:
		
            	polled_sw_version_before = get_valid_version_sc200(polled_sw_version_before)
            else:
		polled_sw_version_before = get_valid_version_m1000(polled_sw_version_before)
       	    for version1 in firmware_version:
		print "firmware_version &&&&&&&&&&&&&&&",firmware_version,version1
        	if len(version1.split('.')) == 2:
            		version = get_valid_version_sc200(version1)
            	else:
            		version = get_valid_version_m1000(version1)

            	if 'x' in  version.lower():
                	version = version.replace('x','(\d+)')
                	version = version.replace('.', '\.')
               	
            	match = re.search(version, polled_sw_version_before)
             	if match:
                	version = match.group()
                	return True
            	return False
    except Exception,error:
        print error ,"update_bit"

def get_valid_version_m1000(polled_version):
    polled_version = polled_version.split('.')
    for i in range (len(polled_version)):
        if len(polled_version[i])==1:
            polled_version[i] = str(00)+str(polled_version[i])
        if len(polled_version[i]) == 2:
            polled_version[i] = str(0)+str(polled_version[i])
    new_version = '.'.join(polled_version)
    return new_version


def get_valid_version_sc200(polled_version):
    polled_version = polled_version.split('.')
    for i in range (len(polled_version)):
        if len(polled_version[i])==1:
            polled_version[i] = str(0)+str(polled_version[i])
        if len(polled_version[i]) == 2:
            polled_version[i] = str(polled_version[i])
    new_version = '.'.join(polled_version)
    return new_version



def get_firmware_version(data):
	site_name = "ospf1_slave_1"
	if data[0]['device_type'] == 'SC200':
		service_name = 'sc200_sw_version_invent'
	else:
		service_name = 'system_sys_swversion_invent'
	version = []
	data_list = []
	cmd = '/omd/sites/%s/bin/cmk -nvp --checks=%s %s' % (str(site_name), service_name,data[0]['device_id'])	
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
	check_output, error = p.communicate()
	if check_output:
		try:
			check_output = filter(lambda t: service_name in t, check_output.split('\n'))
			check_output = check_output[0].split('- ')[1].split(' ')
			version.append(check_output[0].split('=') [1])
			#print check_output,"%%%%%5%%"
		except Exception,error:
			print error	
	if 'polled_sw_version_before' not in data[0]:
		data[0]['polled_sw_version_before'] = ''.join(version)

	else:
		data[0]['polled_sw_version_after'] =''.join(version)  
	logger.info("polled_sw_version_data %s " %(data))
	return data

def update_firmware(firmware_data):
	try:
		update_firmware_data = []
		worng_data = []
		get_data_conf= config.get('Upload Firmware')
		url = get_data_conf['url'] 
		auth_data = auth()
		if auth_data:
			headers = {
				"token":auth_data['access_token'],
				"user_key":auth_data['user_key'],
				"user_id":auth_data['user_id']
			}
			properties =firmware_data[0]['properties'].split(",")
			values = firmware_data[0]['values'].split(",")
			data_dict = dict(zip(properties,values))
			if firmware_data[0]['type'] == 'frm': 
				payload = {
					"apiType": firmware_data[0]['firmware_protocol'],
					"ips":firmware_data[0]['device_ip'],
					"filesPath":str(firmware_data[0]["path"]),
					"fileType":'APP',
					"fileModel": firmware_data[0]["device_type"]
					}
			elif firmware_data[0]['type'] =='icp':                          
                        	payload = {     
					"apiType":  firmware_data[0]['firmware_protocol'],
                                	"ips":firmware_data[0]['device_ip'],
                                	"filesPath":str(firmware_data[0]["path"]),
                                	"fileType": 'APPFILE',
					"fileModel":firmware_data[0]["device_type"]
                               	        }

			elif firmware_data[0]['type'] in [ 'dcc', 'dcf', 'dcs']:
				payload = {
					"apiType": firmware_data[0]['firmware_protocol'],
                                	"ips":firmware_data[0]['device_ip'],
                                 	"filesPath":str(firmware_data[0]["path"]),
                                 	"fileType":'CONFIG',
			 	 	"fileModel": firmware_data[0]["device_type"]
                               		}
			else: 
		       		payload = {
					"apiType":firmware_data[0]['firmware_protocol'],
                               	        "ips":firmware_data[0]['device_ip'],
                                 	"filesPath":str(firmware_data[0]["path"]),
                                 	"fileType":'CONFIG',
                                 	"fileModel": firmware_data[0]["device_type"]
               	                	}
			print payload
			if payload:
				response = requests.post(str(url),headers=headers,data=payload)
				print response
				res = json.loads(response.content)
				print res
				data_value = res["object"]
				print "$$$$$$$$$$$response$$$$$$$$$44",response
			data_value['id']=  firmware_data[0]['id']
                        data_value['device_id'] = firmware_data[0]['device_id']
                        data_value['polled_sw_version_before'] = firmware_data[0]['polled_sw_version_before']
                        data_value["completion_time"] = int(time.time())
                        data_value["ping_status_before"]= 'up'
                        data_value['filename'] =   firmware_data[0]['filename']
			data_value["device_type"]= firmware_data[0]['device_type']
			data_value["file_version"] = firmware_data[0]["file_version"]
			data_value["black_list_bit"] = 0
		logger.info("api data after firmware update %s" % data_value)
	except IOError,e:
		print "error in Auth",e
	
	return data_value

def insert_config(config_data1):
	try:
		insert_data_list = []
		for args in data_value:
			data_list = []
			if int(args['statuscode']) == 200:
				data_list.extend([args['id'],"None","None",args['ping_status_before'],'false',args['ping_status_before'],arcs['completion_time'],args['device_id'],args['filename'],"config update"])
			else:
				data_list.extend([args['id'],"None","None",args['ping_status_before'],'false',args['ping_status_before'],arcs['completion_time'],args['device_id'],args['filename'],"config file not update"]) 
			insert_data_list.append(tuple(data_list))
                cnx = mysql_conn()
                cursor = cnx.cursor()
                query = """INSERT INTO  firmware_schedule_upload_status_history (schedule_id,polled_sw_version_before,polled_sw_version_after,ping_status_before,upload_status,ping_status_after, completion_time,device_id,file_version,upload_status_code)\
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

                update_query = """INSERT INTO  firmware_schedule_upload_status_current (schedule_id,polled_sw_version_before,polled_sw_version_after,ping_status_before,upload_status,ping_status_after, completion_time,device_id,file_version,upload_status_code)\
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                        polled_sw_version_before = VALUES(polled_sw_version_before) , polled_sw_version_after = VALUES(polled_sw_version_after) , ping_status_before = VALUES(ping_status_before) ,upload_status = VALUES(upload_status),\
                        ping_status_after = VALUES(ping_status_after),completion_time = VALUES(completion_time),file_version = VALUES(file_version),upload_status_code = VALUES(upload_status_code);"""


                for args1 in insert_data_list:
                        cursor.execute( query, args1)
                        cursor.execute( update_query, args1)
                        cnx.commit()
                cursor.close()

                cnx.close()
		logger.info("data_insert for config file %s " % insert_data_list )
	except IOError,e:
		
                print "error in Auth",e




def insert_data(data_value):
        try:	
                insert_data_list = [] 
                logger.info("data_insert %s" % data_value)
		
                for args in data_value:
			print "args",args
                        data_list = []

                        if args['ping_status_before'] == "down":# or args['polled_sw_version_before'] == '':
				print "first_if"
                                data_list.extend([args['id'],"None","None",'down','false','down',int(time.time()),args['device_id'],args['filename'],"Device not reachable"])
				print data_list,"data_list"
			elif args['polled_sw_version_before'] == '':
				data_list.extend([args['id'],"None","None",'up','false','up',int(time.time()),args['device_id'],args['filename'],"Unknown firmware version"])

                        elif int(args['black_list_bit']) == 1:
				print "sencond_if"
                                data_list.extend([args['id'],args['polled_sw_version_before'],"None",args['ping_status_before'],'false',"unknown",int(time.time()),args['device_id'],args['filename'],"Firmware version in blacklist"])
			elif int(args['black_list_bit']) == 0 and 'polled_sw_version_after' not in args:
			    if 'invalid_protocol' in args:
				data_list.extend([args['id'],args['polled_sw_version_before'],"None",args['ping_status_before'],'false','up',int(time.time()),args['device_id'],args['filename'],"Invalid protocol"])	     
			    else:
				data_list.extend([args['id'],args['polled_sw_version_before'],"None",args['ping_status_before'],'false','up',int(time.time()),args['device_id'],args['filename'],"Not getting response from controller"])
                        else:
                                if int(args["statuscode"]) == 400:
                                        data_list.extend([args['id'],args['polled_sw_version_before'],args['polled_sw_version_after'],args['ping_status_before'],'false','up',args['completion_time'],args['device_id'],args['filename'],"Wrong ip"])
				elif  int(args["statuscode"]) == 500:
                                        data_list.extend([args['id'],args['polled_sw_version_before'],args['polled_sw_version_after'],args['ping_status_before'],args["status"],'up',args["completion_time"],args['device_id'],args['filename'],"Internal exception"])
                                elif args['polled_sw_version_after'] == args['file_version'] and int(args["statuscode"]) == 200:
                                        data_list.extend([args['id'],args['polled_sw_version_before'],args['polled_sw_version_after'],args['ping_status_before'],args["status"],'up',args['completion_time'],args['device_id'],args['filename'],"Firmware upload successfully"])

                                else:
                                        data_list.extend([args['id'],args['polled_sw_version_before'],args['polled_sw_version_after'],args['ping_status_before'],args["status"],'up',args['completion_time'],args['device_id'],args['filename'],"Firmware staus ok but target version is not matched to current version"])
                        insert_data_list.append(tuple(data_list))
                print insert_data_list,"insertdata"
		
                cnx = mysql_conn()
                cursor = cnx.cursor()
		print "cursor",cursor,cnx
                query = """INSERT INTO  firmware_schedule_upload_status_history (schedule_id,polled_sw_version_before,polled_sw_version_after,ping_status_before,upload_status,ping_status_after, completion_time,device_id,file_version,upload_status_code)\
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

                update_query = """INSERT INTO  firmware_schedule_upload_status_current (schedule_id,polled_sw_version_before,polled_sw_version_after,ping_status_before,upload_status,ping_status_after, completion_time,device_id,file_version,upload_status_code)\
                        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON DUPLICATE KEY UPDATE
                        polled_sw_version_before = VALUES(polled_sw_version_before) , polled_sw_version_after = VALUES(polled_sw_version_after) , ping_status_before = VALUES(ping_status_before) ,upload_status = VALUES(upload_status),\
                        ping_status_after = VALUES(ping_status_after),completion_time = VALUES(completion_time),file_version = VALUES(file_version),upload_status_code = VALUES(upload_status_code);"""
		
                for args1 in insert_data_list:
                        cursor.execute( query, args1)
                        cursor.execute( update_query, args1)
                        cnx.commit()
                cursor.close()

                cnx.close()
		
                logger.info("logger********************end******************************")
        except IOError,e:
                print "error",e

def update_bit(update_bit_data):

        try:

                #print "insert data",update_bit_data
                cnx = mysql_conn()
                cursor = cnx.cursor()
                #update_query = """UPDATE  firmware_schedule_upload set isCompleteStatus = 1 where isCompleteStatus = 0 and device_id = VALUES(device_id) and scheduled_time = VALUES(scheduled_time)
                #VALUES(%s,%s)"""
		logger.info("update_bit_data %s" %update_bit_data)
                for args1 in update_bit_data:
                        update_query = """UPDATE  firmware_schedule_upload set isCompleteStatus = 1 where isCompleteStatus = 0 and device_id = %s and scheduled_time = %s""" %(args1['device_id'],args1['scheduled_time'])
                        cursor.execute(update_query)
                        cnx.commit()
                cursor.close()
                cnx.close()
		logger.info("update_query %s" %update_query)
        except Exception,error:
                print error ,"update_bit"

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
        #max_cycle=Config.get('max_cycles','cycles')

        try:
                mysql_conn = mysql.connector.connect(host=str(host_name["host"]),user=str(user_name['Name']), database=str(db_name['db_name']),password=str(password["Pass"]), port= str(port_no['port']))

        except Exception,error:
                print error

        return mysql_conn

if __name__ == '__main__':
	try:
		logger.info("logger***********start****************logger")
		valid_data = []
		invalid_data = []
		get_data_conf= config.get('Get Data')
		url = get_data_conf['get_data_url'] 
		auth_data = auth()
		print auth_data
		if auth_data:
			headers = {
				"token":auth_data['access_token'],
				"user_key":auth_data['user_key'],
				"user_id":auth_data['user_id']
			}
		payload = {	
			"start_date":int(int(time.time()) - 300),
			"end_date":int(time.time()),
			"limit":100,
			"offset":0,
			"in_device_type":0,
			}
		print headers,payload
		response = requests.post(str(url),headers=headers,data=payload)
		res = json.loads(response.content)
		data = res["object"]
		#print data,"starting data"
		logger.info("get_firmware data %s" %data)
		if data:
			data1 = []
			for split_data in data:
				device_ip_list = split_data["device_ip"].split(",")
				device_id_list = split_data["device_id"].split(",")
				schedule_id_list = split_data['id'].split(",")	
				firmware_protocol = split_data['values'].split(",")	
				print firmware_protocol
				for ip in range(len(device_ip_list)):
					data_dict = split_data
					data_dict['device_ip'] = device_ip_list[ip]
					data_dict['device_id'] = device_id_list[ip]
					data_dict['id'] = schedule_id_list[ip]
					if firmware_protocol[ip] == "":
						data_dict["firmware_protocol"] = "http"
					else: 
						data_dict["firmware_protocol"] = firmware_protocol[ip]
					data1.append(data_dict.copy())
			
			data_list = []
			logger.info("get_firmware data %s" % data1)
			update_bit(data1)
			for data2 in data1:
		    		if int(data2["isCompleteStatus"]) ==0 :
					data_list.append(data2)
       			thread_count = config.get('Thread_count')			
	
			#print thread_count,thread_count['count'],type(thread_count['count'])
			#thread_count = 3
			#update_bit(data_list)

			executor = concurrent.futures.ThreadPoolExecutor(max_workers=int(thread_count['count']))
			start_time = time.time()
			count = 0 
			#print (data)	
			print len(data_list),"%^^^^^^^^^^^^^^^^^^^^^^^",data_list	
			for i in data_list:
				executor.submit(get_schedule_firmware_list,i)
		   		count  = count + 1
			print count 
		
	except IOError,e:
		print "error in Auth",e
