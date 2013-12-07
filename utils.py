
import re
regex = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')

def ipv4_type(value):
    if not regex.search(value):
        raise ValueError(u"Invalid IP address: {}".format(value))
    return value
