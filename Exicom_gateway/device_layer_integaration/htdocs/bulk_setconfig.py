#from pysnmp.entity.rfc3413.oneliner import cmdgen
#from pysnmp.proto.rfc1902 import *
from pysnmp.hlapi import *
#from pysnmp.hlapi.asyncio import Udp6TransportTarget
from ast import literal_eval
import unicodedata
from multiprocessing import Process,Queue
from wato import *
import time
import mysql.connector
from nocout_logger import nocout_log
from configobj import ConfigObj
logger = nocout_log()
import json
#TODO integrate code with OMD apache 
from pprint import pformat
import requests
config = ConfigObj("/omd/sites/ospf1_slave_1/share/check_mk/web/htdocs/conf.ini")

def auth():
    """
        This method Authentication user is valid or not 
        if user is valid then return auth_data
    """
    try:
        auth_conf= config.get('User Authentication')
        payload = {"user_name":auth_conf['user_id'],
                   "password":auth_conf['password'],
                   "application_id":auth_conf['application_id']
                  }
        url = auth_conf['Auth_URL']
        response = requests.post(str(url), data=payload)
        res = json.loads(response.content)
        logger.info(res)
        auth_data = res["object"]

    except Exception, err:
        logger.error('Error in authentication api : %s' %err)
    return auth_data

def get_ip_type(device_id):
    try:
        site_config = generic_config()
        db = mysql_conn(site_config, default_db = False, db_name = 'xfusion_metadata')
        query =  "SELECT value FROM xfusion_metadata.device_device_properties_value where device_id = %s and properties_id = 102;" % device_id
        cursor = db.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        logger.error("IP-TYPE %s " % (data))
    except Exception,e:
        logger.error("Error in getting data from mysql %s" % (e))
    else:
        return data[0][0]


def bulkconfig(q,**kwargs):
    """
    BulkConfig for setting multiple Oids on multiple devices
    

    """

    device_oid_dict = kwargs['oid_dict']
    device_oids = kwargs['device_oids']
    var = make_varbinds(device_oid_dict,device_oids)
    result_dict = {}
    auth_detail = auth()
    if var:
	for device_id,device_ip,oid in device_oids:

	    try:
		#community_string = get_community_string(device_id)
		ip_type = get_ip_type(device_id)
		#logger.error("Received community string : %s"%community_string)
	        oid_varbinds = var.get((device_id,device_ip,oid))
		#logger.info("oid_varbinds %s" %oid_varbinds)    
	        device_oid_value = device_oid_dict.get((device_id,device_ip,oid))
	        job_id = device_oid_value[2]
	    
	        current_time = int(time.time())
                if oid_varbinds == None:
			logger.error("Error: Incorrect value for specified type on device ip %s id %s" % (device_ip,device_id))
			result_dict[job_id] = (4,current_time,job_id)
			continue
	    except Excpeption,e:
		logger.error("Error in parsing varbinds %s for ip %s id %s" % (e,device_ip,device_id))
		continue

	    try:
		logger.info("%%%%%%")
		if ip_type.lower() == 'ip-v6':
		    udp_func = Udp6TransportTarget((device_ip, 161))
		elif ip_type.lower() == 'ip-v4':
		    udp_func = UdpTransportTarget((device_ip, 161))

		if auth_detail:
		    headers = {
                    "token":auth_detail['access_token'],
                    "user_key":auth_detail['user_key'],
                    "user_id":auth_detail['user_id']
                    }
	            payload = {
                    "device_id":device_id,
                    }
		    get_properties = config.get('device_properties')
		    logger.error("properties : %s"%str(get_properties))
		    url = get_properties['device_properties_value']
		    logger.error("url : %s"%str(url))
	            response = requests.post(str(url),headers=headers,data= payload)
		    logger.error("response : %s"%str(response))
		    logger.error("response content : %s"%str(response.content))
        	    res = json.loads(response.content)
            	    logger.error("&&&&&&&&&&&&&&&&&&&&&&&&&&&& res data %res" %res)
            	    device_properties = res["object"][0]
                    if device_properties['hardware_version'].lower() != 'v3':
			snmp_gen = setCmd(
			    SnmpEngine(),
			    CommunityData(str(device_properties['Write_Community']), mpModel=1),
			    udp_func,
			    ContextData(),
			    oid_varbinds)
		    else:
			try:
                            auth_protocol_details = {'md5':usmHMACMD5AuthProtocol,'sha':usmHMACSHAAuthProtocol,'noauth':usmNoAuthProtocol}
                            priv_protocol_details = {'des':usmDESPrivProtocol,'aes':usmAesCfb128Protocol,'nopriv':usmNoPrivProtocol}
                            auth_protocol = device_properties["Auth_Protocol"].lower()   
                            priv_protocol = device_properties["Privacy_Protocol"].lower()
                            if auth_protocol in ["md5","sha"]:
                    	    	auth_value = auth_protocol_details[auth_protocol]
                            else:
                            	auth_value = usmNoAuthProtocol

                    	    if priv_protocol in ["des","aes"]:
                            	print priv_protocol
                            	priv_value = priv_protocol_details[priv_protocol]
                    	    else:
                            	priv_value = usmNoPrivProtocol
			except Excpeption,e:
                	    logger.error("Error in device_properties %s " %device_properties)
                	    continue
			logger.error("device_properties************* %s" %device_properties)
			if str(device_properties['V3_Security_Model']) == 'Authentication and Privacy':
			    logger.error("***********in if condition*******")
			    snmp_gen = setCmd(SnmpEngine(),
		           	UsmUserData(str(device_properties['Security_Name']), str(device_properties['Auth_Password']),str(device_properties['Privacy_Password']),\
				authProtocol=auth_value,privProtocol=priv_value),      
        			udp_func,
           			ContextData(),
           			oid_varbinds)


			elif str(device_properties['V3_Security_Model']) == 'Authentication and No Privacy':
                            snmp_gen = setCmd(SnmpEngine(),
                                UsmUserData(str(device_properties['Security_Name']), str(device_properties['Auth_Password']),\
				authProtocol=auth_value,privProtocol=priv_value),
                                udp_func,
                                ContextData(),
                                oid_varbinds)
	
			else:
                            snmp_gen = setCmd(SnmpEngine(),
                                UsmUserData(str(device_properties['Security_Name']),authProtocol=auth_value,privProtocol=priv_value),
                                udp_func,
                                ContextData(),
                                oid_varbinds)

		error_indication, error_status, error_index, varbinds = next(snmp_gen)
                logger.error("error_indication : %s"%error_indication)
                logger.error("error_status : %s"%error_status)
                logger.error("error_index : %s"%error_index)
                logger.error("varbinds : %s"%varbinds)
	    except Exception,e:
		result_dict[job_id] = (4,current_time,job_id)
		logger.error("Error in snmpSet command %s" % e)
                q.put(result_dict)
		continue	

	    if error_indication:
		logger.error("Error: %s on device ip %s id %s" % (error_indication,device_ip,device_id)) 
		result_dict[job_id] = (4,current_time,job_id)

	    if error_status:
		logger.error('%s at %s' % (
				    error_status.prettyPrint(),
					    error_index and varbinds[int(error_index)-1] or '?'))
		result_dict[job_id] = (4,current_time,job_id)
	    if not result_dict.get(job_id):
		value = get_value(device_id,device_ip,oid)
		try :
			set_value = str(device_oid_value[1])
			value = literal_eval(value)
			set_value = literal_eval(set_value)
		except Exception, e :
			pass
		logger.error("Get value : "+str(value))
		logger.error("Set value : "+str(set_value))
		
		if value == set_value: 
		    result_dict[job_id] = (2,current_time,job_id)
		else :
		    logger.error("No error in snmpset but value not set on device")
		    result_dict[job_id] = (4,current_time,job_id)
		logger.error("result_dict %s:%s"%(job_id,result_dict[job_id]))
        q.put(result_dict)

def get_value(device_id,device_ip,oid) :
    try:
    	cmd = 'cmk --snmpget %s %s' % (oid, int(device_id))
    	print cmd
    	logger.info(cmd)
    	p = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    	check_output, error = p.communicate()
    	logger.info(' Check_output: ' + check_output.split('):')[-1].strip())
    	return check_output.split('):')[-1].strip().replace("'","")
    except Exception,e:
	logger.error("Error in get_value %s" %e)
def make_varbinds(oid_dict,device_oids):
    """
    Make Varbinds with multiple oids

    """
    varbinds = {}
    error = 0
    logger.info("VarBinds formation for oids %s --%s " % (device_oids,oid_dict))
    for device_id,device_ip,oid in device_oids:

	try:
            oid_type_value = oid_dict.get((device_id,device_ip,oid))  
	    oid_type = oid_type_value[0]
	    oid_value = oid_type_value[1]
        
	    if 'STRING' in oid_type.upper():
	        d_type = OctetString
            elif 'INTEGER' in oid_type.upper():
                d_type = Integer32
	    elif 'COUNTER32' in oid_type.upper():
	        d_type = Counter32
	    elif 'INETADDRESS' in oid_type.upper():
                d_type = IpAddress
            else:
	        d_type = OctetString
	    logger.error("oid_value %s " % d_type)

	    if type(oid_value) is str:
                oid_value = unicode(oid_value, "utf-8")
            oid_value = unicodedata.normalize('NFKD',oid_value).encode('ascii', 'ignore')

	    logger.error("oid_value %s " % oid_value)
            if not oid_value:
                oid_value = ''
            varbinds[(device_id,device_ip,oid)] = (ObjectType(ObjectIdentity(oid),d_type(oid_value)))
        except Exception,e:
	    logger.error("Error in making varbinds %s" % e )
	    varbinds[(device_id,device_ip,oid)] = None
	    continue
    logger.info("varbinds {0}".format(varbinds))
    
    return varbinds








def mysql_conn(site_config, default_db = True, db_name = None):
    """
    Function to create connection to mysql database

    Args:
        db (dict): Mysqldb connection object

    Kwargs:
        kwargs (dict): Dict to store mysql connection variables
    """
    try:
        ip = site_config.get('ip')
        mysql_port = site_config.get('mysql_port')
        sql_passwd  =  site_config.get('sql_passwd')
	if default_db :
            db = site_config.get('exicom_db')
	else :
	    db = db_name
        user = site_config.get('user')
        db_conn = mysql.connector.connect(
                user=user,
                passwd=sql_passwd,
                host=ip,
                db=db,
                port=mysql_port,
                buffered=True
        )
    except mysql.connector.Error as err:
        raise mysql.connector.Error, err
    logger.info("DB connection : %s"% str([user,sql_passwd,ip,db,mysql_port]))
    return db_conn






def update_mysql_bulkconfig(response,metadata,bulkconfig_insert_table,bulkconfig_update_table,site_config):
    """
    update bulkconfig set w.r.t job id in mysql for SUCCESS/FAILURE
    insert entry for each success/failure result in insert table to track history
    
    """

    if response: 
	try:
            insertion_dict = {}
	    update_result = []
	    for entry in response:
                entry_result = entry.values()
		update_result.extend(entry_result)
                for j_id in entry:
	            if j_id in metadata:
	                insertion_dict[j_id] = metadata.get(j_id) + entry.get(j_id)[:-1]
   
            insertion_result = insertion_dict.values() 
   	except Exception,e:
	    logger.error("Error in mysql insertion parsing %s "% e)
 
        update_query = "UPDATE IGNORE `%s` " % bulkconfig_update_table
        update_query += """SET `status`=%s, `completion_time`=%s WHERE `id`=%s """
  
        insert_query = "INSERT INTO `%s` " %  bulkconfig_insert_table
        insert_query += """
    		(oid_id,creation_time,job_user,scheduled_time,ip_address,job_description,value,device_id,status,completion_time) 
    		VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
    	     """
	try:
	    db = mysql_conn(site_config)
	    cursor = db.cursor()
	    cursor.executemany(update_query,update_result)
	except mysql.connector.Error as err:
	    raise mysql.connector.Error, err
	    logger.error("Error in mysql insertion")
	else:
	    db.commit()

	try:
	    cursor.executemany(insert_query,insertion_result)
        except mysql.connector.Error as err:
            raise mysql.connector.Error, err
        else:
	    db.commit()

	logger.error("Bulk Config finish")
    else:
	logger.error("Response is not Generated")


def set_bulkconfig(oid_dict):
    """
    Multiprocessing for handling request for multiple devices and oids

    """
    #device_list = literal_eval(html.var('device_list'))
    #oid_dict = literal_eval(html.var('oid_dict'))
    #mysql_id = literal_eval(html.var('update_id'))
    response = []
    device_oids  = oid_dict.keys()
    device_count = len(device_oids)
    q = Queue()

    logger.info("total device count for bulkconfig %s" % device_count)
    jobs = [ Process(
		target = bulkconfig,
		args = (q,),
		kwargs = {
			'device_oids' : device_oids[i:i+500],
			'oid_dict': oid_dict
			}
		) for i in xrange(0,device_count,500)
        ] 
    for j in jobs:
	j.start()
    for k in jobs:
	k.join()

    while True:
	if not q.empty():
	    response.append(q.get())
	else:
	    break

    return response


def generic_config():
    site = 'ospf1_slave_1'
    config = ConfigObj('/omd/sites/ospf1_slave_1/nocout/conf.d/%s' % 'ospf1.ini')
    site_config = config.get(site)
    return site_config
	
	
def process_scheduled_jobs():
    """
    Get scheduled jobs from the table in every half an hour for bulk configset with snmp

    """
    
    site_config = generic_config()

    c_time = int(time.time())
    previous_time = c_time - 1800
    bulkconfig_insert_table =  site_config.get('bulkconfig').get('table_name')
    bulkconfig_update_table = site_config.get('bulkconfig_status').get('table_name')
    #oid_table = site_config.get('oid_table')

    query ="""select bulkconfig.id,
	 	bulkconfig.ip_address,
		oid_l.oid,
		oid_l.type,
		bulkconfig.value,
		bulkconfig.oid_id, 
		bulkconfig.creation_time,
		bulkconfig.user_id,
		bulkconfig.scheduled_time from %s AS bulkconfig""" % (bulkconfig_update_table)
    query += """ Left join %s as oid_l on oid_l.id = bulkconfig.oid_id """ % ("oid_list")
    query += """where bulkconfig.scheduled_time < %s and bulkconfig.scheduled_time >= %s and bulkconfig.status=1""" % (c_time,previous_time)    
    
    try:
        db = mysql_conn(site_config)
        cursor = db.cursor()
        cursor.execute(query)
	data = cursor.fetchall()
        config_dict = {}
	job_metadata = {}
        for entry in data:
           job_id,ip,oid,oid_type,value  = entry[0],entry[1],entry[2],entry[3],entry[4]
	   metadata = entry[5],entry[6],entry[7],entry[8],entry[1],"snmpset",entry[4] #oid_list id,creation_time,userid,scheduled time,ip,value
	   config_dict[(ip,oid)] = (oid_type,value,job_id)
	   job_metadata[job_id] = metadata
    except Exception,e:
	print e
    # Call bulkconfig module
    logger.error("processing bulk config request")
    response = set_bulkconfig(config_dict) 
    update_mysql_bulkconfig(response,job_metadata,bulkconfig_insert_table,bulkconfig_update_table,site_config)



def live_setconfig():
    """
    Api calling function from the UI application to set bulk config
	
    oid_dict =
 	{
       		('192.168.10.53','.1.3.6.1.4.1.38016.14.2.11.17.0'): ('OCTET STRING','110',1),# (oid_type,value,update_table_id)
       		('192.168.10.53','.1.3.6.1.4.1.38016.14.2.11.18.0'): ('OCTET STRING','111',2)
	}
    metadata =
	{
		1:(34, 1526554631, u'1', 1526559931, u'192.168.10.53', 'snmpset', u'110'),#(oid_list id,creation_time,user_id,schedule_time
		2: (35, 1526554631, u'1', 1526559931, u'192.168.10.53', 'snmpset', u'111')  ip,job description,value )
	}

    [{
     device_device_ipaddress: "172.16.67.121"
     name:"controllerReset"
     oid:".1.3.6.1.4.1.38016.14.1.7"
     oidid:4
     value:"3",
     type:"OCTET STRING",
     jobDesc:'snmpset',
     rowId:31,
     userId: 3,
     creationTime:1212312312,
     scheduledTime:341123313,
     },...{}

     ]



    """    



    logger.error("bulk config start %s" % html.var('device_oid_list'))
    msg_response = {
		"status" : "success",
		"message": "successfully received scheduled job request",
		"valid": "true"
             }

    try:
	logger.error("type of received object %s " % (html.var('device_oid_list')))
        device_oid_list = eval(html.var('device_oid_list'))
    except Exception,e:
        logger.error("Error in correct format of payload received %s" % e)
	msg_response["status"] = "Failure"
	msg_response["message"] = e	
        return html.write(pformat(msg_response))

    oid_dict ={}
    metadata = {}
    device_id = None
    try:
        for device_info in device_oid_list:
	    logger.info("********* %s " %device_info)
	    ip = device_info['ip_address']
	    oid = device_info['oid']
            oid_type = device_info['type']
	    value = device_info['value']
	    rowid = int(device_info['rowId'])
	    creation_time = device_info['creationTime'] 
 	    scheduled_time = device_info['scheduledTime'] 
	    user_id = device_info['userId'] 
	    job_desc = device_info['jobDesc'] 
	    oidid = device_info['oidid']
	    try:
	        device_id = device_info['device_id'] 
	    except Exception,e:
		logger.error("Error in while getting device id")
            oid_dict[(device_id,ip,oid)] = (oid_type,value,rowid)
	    metadata[rowid] = (oidid,creation_time,user_id,scheduled_time,ip,job_desc,value,device_id) 
    except Exception,e:
	logger.error("Error in parsing api payload  %s" % e)
	msg_response["status"] = "Failure"	
	msg_response["message"] = e
        return html.write(pformat(msg_response))
    
    logger.info("After parsing data %s -- %s" % (metadata,oid_dict))
    site_config = generic_config()
    
    bulkconfig_insert_table =  site_config.get('bulkconfig').get('table_name')
    bulkconfig_update_table = site_config.get('bulkconfig_status').get('table_name')
    
    
    logger.info("processing bulk config request")


    # Get response from bulkconfig
    response = set_bulkconfig(oid_dict) 
    
    logger.info("Received response after bulkconfig %s " %  response)

    if response:
    	# update mysql for bulkconfig
        update_mysql_bulkconfig(response,metadata,bulkconfig_insert_table,bulkconfig_update_table,site_config)
    else:
	msg_response["status"]  = "failure"
    return html.write(pformat(msg_response))

if __name__ == '__main__':
    oid_dict = {
    	('192.168.10.53','.1.3.6.1.4.1.38016.14.2.11.17.0'): ('OCTET STRING','150',3), # {ip:oid}: (type,value,mysql_id)
    	('192.168.10.53','.1.3.6.1.4.1.38016.14.2.11.18.0'): ('OCTET STRING','150',4)}

    #result = set_bulkconfig(oid_dict)
    #print "{0}".format(result)	
    process_scheduled_jobs()
    
