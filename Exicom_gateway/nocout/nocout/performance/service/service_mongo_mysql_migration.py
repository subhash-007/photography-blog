import subprocess
import os

arg=["python /omd/sites/ospf1_slave_1/nocout/performance/service/rrd_migration.py","python /omd/sites/ospf1_slave_1/nocout/performace/service/migrations.py"]

for item in arg:
	subprocess.Popen(item,shell=True)


##rrd_miogration ---------------------------
#child=subprocess.Popen("python /omd/sites/ospf1_slave_1/nocout/performance/service/rrd_migration.py",shell=True)

#print "2nd  script--------------"

#i# migration -----------------------------
#child2=subprocess.Popen("python /omd/sites/ospf1_slave_1/nocout/performance/service/migrations.py 2",shell=True)
