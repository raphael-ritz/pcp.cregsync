# explicit mappings of creg ids to dp ids

cid2dpid = {
    4:'CINECA',
    5:'CSC',
    6:'CINES',
    7:'STFC',
    8:'SURFsara',
    9:'SIGMA--UiO',
    10:'KIT',
    11:'mpcdf',
    12:'UEDIN--EPCC',
    13:'MPI--PL',
    14:'PSNC',
    15:'DKRZ',
    16:'EKUT',
    17:'INGV',
    18:'JUELICH',
    19:'UCL',
    20:'SNIC',  # or should this be called PDC?
    21:'BSC',
    161:'GRNET',
    181:'Trust--IT',
    201:'GFZ',
}

# map creg:site keys to dp:provider keys
# the default is to use creg keys in lower case directly

sitekeys2dp = {
    'description':'text',
    'alarmemail':'alarm_email',
    'emergencytel':'emergency_phone',
    'helpdeskemail':'helpdesk_email',
    'homeurl':'url',
    'iprange':'ip4range',
    'officialname':'description',
}

# map creg:service keys to dp:registered_service_component keys
# the default is to use creg keys in lower case directly

servicekeys2dp = {
    'architecture':'host_architecture',
    'dn':'host_dn',
    'hostname':'host_name',
    'ipaddress':'host_ip4',
    'ipv6address':'host_ip6',
    'operatingsystem':'host_os',
    'url':'service_url',
}

# manually maintained mapping of service types

servicetypes = {
    1:"MyProxy",
    2:"eudat.registry.gocdb",
    3:"WebServer",
    4:"SVN",
    5:"Wiki",
    7:"TTS",
    11:"NSCA-client",
    44:"b2access.openid-bridge",
    48:"b2safe.irods",
    49:"b2safe.dsi",
    50:"b2stage.gridftp",
    51:"b2handle.handle.api",
    52:"b2host.ssh-gateway",
    41:"b2access.unity",
    42:"b2access.oauth",
    43:"b2access.ca",
    45:"b2drop.owncloud",
    46:"b2find.ckan",
    47:"b2share.invenio",
    71:"b2gether.cms.confluence",
    78:"eudat.coord.dpcp",
    69:"b2handle.handle.resolver",
    70:"b2gether.cms.drupal",
    72:"b2gether.codeRep.svn",
    73:"b2gether.codeRep.git",
    74:"b2gether.its.jira",
    75:"b2access.myproxy",
    76:"b2access.crowd",
    77:"eudat.helpdesk.rt",
}
