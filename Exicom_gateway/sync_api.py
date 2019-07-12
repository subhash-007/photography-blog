import requests
api_url= "http://omdadmin:omd@127.0.0.1:5000/ospf1_slave_1/check_mk/nocout.py"
data ={'mode':'sync'}
response = requests.post(api_url,data=data)
#print response
