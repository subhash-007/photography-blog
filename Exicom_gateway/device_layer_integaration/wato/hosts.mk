# Written by WATO
# encoding: utf-8

all_hosts += [

 "1|snmp-only|prod|snmp|lan|wato|/" + FOLDER_PATH + "/",
  #"2|snmp-only|prod|snmp|lan|wato|/" + FOLDER_PATH + "/",
  "2|M1000|wan|prod|snmp-v2|snmp|site:ospf1_slave_1|wato|//",
  "3|M2000|wan|prod|snmp-v2|snmp|site:ospf1_slave_1|wato|//",
  "4|M3000|wan|prod|snmp-v2|snmp|site:ospf1_slave_1|wato|//"
]

# Explicit IP addresses
ipaddresses.update({'1': u'127.0.0.1', '2': u'192.168.10.53','3':u'192.168.10.53','4':'192.168.1.38'})

# Explicit SNMP communities
explicit_snmp_communities.update({'1': u'public', '2': u'public','3':u'public','4':u'public'})

# Host attributes (needed for WATO)
host_attributes.update(
{'1': {'alias': u'',
       'ipaddress': u'127.0.0.1',
       'snmp_community': u'public',
       'tag_agent': 'snmp-only'},
 '2': {'alias':'M1000',
       'ipaddress': u'192.168.10.53',
       'snmp_community': u'public',
       'site':'ospf1_slave_1',
       'tag_agent': 'snmp-v2|snmp'},
 '3': {'alias':'M2000',
       'ipaddress': u'192.168.10.53',
       'snmp_community': u'public',
       'site':'ospf1_slave_1',
       'tag_agent': 'snmp-v2|snmp'},
 '4': {'alias':'M3000',
       'ipaddress': u'192.168.1.38',
       'snmp_community': u'public',
       'site':'ospf1_slave_1',
       'tag_agent': 'snmp-v2|snmp'}})
