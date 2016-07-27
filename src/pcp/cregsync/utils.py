import csv
import json
import logging
import argparse
import requests
from collections import defaultdict

from Products.PlonePAS.utils import cleanId
from AccessControl.SecurityManagement import newSecurityManager
from Testing import makerequest

from zope.component.hooks import setSite

from pcp.cregsync import config


def getArgParser():
    parser = argparse.ArgumentParser(description='The cregsync package provides scripts to '\
                                     'transfer data from the central registry to '\
                                     'the data project coordination portal.')
    parser.add_argument("-s", "--site_id", default="pcp", 
                        help="internal id of the Plone site object (default: 'pcp')")
    parser.add_argument("-p", "--path", default="data/GOCDB/20160726/", 
                        help="relative path to the input data directory "\
                        "(default: 'data/GOCDB/20160726/')")
    parser.add_argument("-f", "--filename", default="", 
                        help="name of the input data file "\
                        "(default: '' - aka not set)")
    parser.add_argument("-a", "--admin_id", default="creg", 
                        help="all changes and additions will be shown as from this user"\
                        " (default: 'creg')")
    parser.add_argument("-t", "--top", action='store_true',
                        help="Sync only the top-level service - no details")
    parser.add_argument("-d", "--dry", action='store_true',
                        help="dry run aka nothing is saved to the database")
    parser.add_argument("-c", "--command", 
                        help="name of the script invoked. Set automatically. It is here"\
                        "to keep the 'argparse' module happy")
    return parser

def getLogger(logfilename='var/log/cregsync.log'):
    logger = logging.getLogger('cregsync')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logfilename)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    # create formatter and add it to the handlers
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(file_formatter)
    ch.setFormatter(console_formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def getSite(app, site_id, admin_id):
    app = makerequest.makerequest(app)
    admin = app.acl_users.getUser(admin_id)
    if admin is None:
        admin = app[site_id].acl_users.getUser(admin_id)
    admin = admin.__of__(app[site_id].acl_users)
    newSecurityManager(None, admin)

    site = app.get(site_id, None)

    if site is None:
        print "'%s' not found (maybe a typo?)." % site_id
        print "To create a site call 'import_structure' first."
        raise ValueError

    setSite(site)  # enable lookup of local components

    return site
    

def getData(path, filename):
    """return a DictReader to iterate over the data"""
    source = open(path+filename,'r')
    return csv.DictReader(source)

def getServiceData(path, filename):
    """return a list of dictionaries with the service data"""
    source = open(path+filename,'r')
    raw = json.load(source)
    return raw['data']['services']

def getProperties(path, filename):
    """
    Return a dict keyed by creg:service id pointing to a 
    list of dicts with the additional kv pairs.
    """
    source = open(path+filename,'r')
    reader = csv.reader(source)
    result = defaultdict(list)
    for line in reader:
        result[line[-1]].append(dict(key=line[1],value=line[2]))
    return result
    
def email2puid(site):
    """
    Return a mapping email -> UID for all exisitng Person objects.
    If an email address occurs several times only the first hit is
    recorded and a warning is logged.
    """
    logger = logging.getLogger('contacts')
    result = {}
    for person in site.people.contentValues():
        email = person.getEmail().lower()
        uid =  person.UID()
        if email and email in result.keys():
            logger.warning("'%s' already found - skipping" % email)
            continue
        logger.debug("Mapping '%s' to '%s'" % (email, uid))
        result[email] = uid
    return result.copy()

def makeGenericContact(site, fields, contact_type='generic'):
    logger = logging.getLogger('contacts')
    try:
        provider_id = fields['shortname']
    except KeyError:
        parentsite_id = fields['parentsite_id']
        provider_id = config.cid2dpid[int(parentsite_id)]
    if contact_type == 'security':
        email = fields['csirtemail']
        phone = {'type':'Office', 'number':fields['csirttel']}
        lastname = "Security Contact"
    elif contact_type == 'support':
        email = fields['email']
        phone = {}
        lastname = "Support Contact"
    else:
        email = fields['email']
        phone = {'type':'Office','number':fields['telephone']}
        lastname = "Contact"
    title = ' '.join([provider_id, lastname])
    id = cleanId(title)
    description = "Generic %s details for %s" % (lastname.lower(), provider_id)
    data = {'title':title,
            'description':description,
            'name':dict(firstname=provider_id, lastname=lastname),
            'email':email,
            'phone':[phone],
        }
    if id in site.people.objectIds():
        return site.people[id].UID()
    site.people.invokeFactory('Person', id)
    logger.info("Added %s to the people folder" % id)
    site.people[id].edit(**data)
    logger.debug(data)
    logger.info("Updated %s in the people folder" % id)
    site.people[id].reindexObject()
    return site.people[id].UID()
    

def fixContact(site, fields, contact_type='generic'):
    """
    Generate a generic contact if possible and return its UID.
    Returns None otherwise.
    """
    if contact_type == 'security':
        email = fields['csirtemail']
        return makeGenericContact(site, fields, contact_type='security')
    elif contact_type == 'support':
        return makeGenericContact(site, fields, contact_type='support')
    else:
        email = fields['email']
        return makeGenericContact(site, fields)
    return None

def email2userpk(data):
    """return mapping to enable user_pk lookup by email.
    Assumes 'data' to hold the 'auth.user' data from RCT"""
    result = {}
    for pk, values in data.items():
        email = values['fields']['email']
        result[email] = pk
    return result.copy()

def update(old, item):
    """Helper method to update and exisiting entry in a list of dicts.
    Called by extend for the 'additional' field.
    We know already that 'old' contains an entry with the same key
    as 'item'.
    """
    k = item['key']
    v = item['value']
    for entry in old:
        if entry['key'] == k:
            entry['value'] = v
    return old
        

def extend(old, new):
    """Helper method to extend a list of dicts such that the
    key values do not get duplicated.
    Needed to keep additional entries across updates.
    'old' and 'new' are lists of dicts with keys 'key' and 'value'"""

    existing_keys = [entry['key'] for entry in old]
    for item in new:
        k = item['key']
        v = item['value']
        if k not in existing_keys:
            old.append(item.copy())
        else:
            update(old, item)
    return old

def resolveServiceType(id):
    """Look up the service types from the config"""
    return config.servicetypes[id]
                
def resolve_creg_id(sid, portal_type, context):
    catalog = context.portal_catalog
    items = [e.getObject() for e in catalog(portal_type=portal_type)]
    for item in items:
        additional = item.getAdditional()
        creg_id = 0
        for entry in additional:
            if entry['key'] == 'creg_id':
                creg_id = entry['value']
        if int(creg_id) == int(sid):
            return item.UID()
    return None

def prepare_links(clinks, context):
    """Helper method turning the RS2RSC link table from creg
    into a dict keyed by RS uid holding a list of target RSC uids.
    Objects to be linked have to exist already. 
    """
    result = defaultdict(list)
    for entry in clinks:
        rs_uid = resolve_creg_id(entry['SERVICEGROUP_ID'], 'RegisteredService', context)
        if rs_uid is None:
            print "No registered service with creg_id = '%s' found." % entry['SERVICEGROUP_ID']
            continue
        rsc_uid = resolve_creg_id(entry['SERVICE_ID'], 'RegisteredServiceComponent', context)
        if rsc_uid is None:
            print "No registered service component with creg_id = '%s' found." % entry['SERVICE_ID']
            continue
        result[rs_uid].append(rsc_uid)
    return result.copy()

def getSTT(id, context):
    """Look up the title of the term specified by id in the service types vocabulary"""
    vocab = context.portal_vocabularies['service_types']
    return vocab[id].Title()

# interact with SPMT

def getDataFromSPMT(url):
    """Returns the payload from url or None.
    Never fails."""
    
    r = requests.get(url)
    d = json.loads(r.content)
    try:
        return d['data']
    except KeyError:
        # TODO add logging
        return None
