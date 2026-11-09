def t23_name(name):
 return {'B1 (rsh-α0)':'B1','rabbit-pilot (历史参照)':'rabbit-pilot','neutron-pilot (历史参照)':'neutron-pilot'}.get(name,name)
def t22_start(record):
 value=record.get('start')
 return value if isinstance(value,str) and value else record.get('start_member',record['member'])
