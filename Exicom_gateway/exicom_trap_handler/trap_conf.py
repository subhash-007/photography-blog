"""
Config file containing MySQL DB connection parameter details for each connection type
"""
# connection to snmptt database
snmptt = {
        'host': '182.75.32.210',
        'port': 3307,
        'user': 'root',
	'password': 'Ttpl@123',
        'database': 'snmp_traps'
}

# connection to application database
conf_db = {
        'host': '182.75.32.210',
        'port': 3307,
        'user': 'root',
        'password': 'Ttpl@123',
        'database': 'xfusion_metadata'
}

# connection to processed traps database, historical
processed_traps = {
        'host': '182.75.32.210',
        'port': 3307,
        'user': 'root',
        'password': 'Ttpl@123',
        'database': ' xfusion_performance_spider'
}
mat_db =  {
        'host': '182.75.32.210',
        'port': 3307,
        'user': 'root',
        'password': 'Ttpl@123',
        'database': 'exicom'
}

mongo_db ={
	'host':'127.0.0.1',
	'port':'27017',
	#'database':'aralm_escalation'	
}
