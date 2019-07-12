import os


p = os.path.dirname(os.path.abspath(__file__))

paths = [path for path in p.split('/')]

nocout_site_name = paths[paths.index('sites') + 1]
