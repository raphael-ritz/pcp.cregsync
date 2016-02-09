import csv
import logging
import argparse
from collections import defaultdict

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
    parser.add_argument("-p", "--path", default="data/GOCDB/gocdb_54_dump/", 
                        help="relative path to the input data directory "\
                        "(default: 'data/GOCDB/gocdb_54_dump/')")
    parser.add_argument("-f", "--filename", default="SITES_DATA_TABLE.csv", 
                        help="name of the input data file "\
                        "(default: 'SITES_DATA_TABLE.csv')")
    parser.add_argument("-a", "--admin_id", default="admin", 
                        help="all changes and additions will be shown as from this user"\
                        " (default: 'admin')")
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
    admin = admin.__of__(app.acl_users)
    newSecurityManager(None, admin)

    site = app.get(site_id, None)

    if site is None:
        print "'%s' not found (maybe a typo?)." % site_id
        print "To create a site call 'import_structure' first."
        raise ValueError

    setSite(site)  # enable lookup of local components

    return site
    

def getData(path, filename):
    # TODO: this needs to be adjusted for CSV data
    source = open(path+filename,'r')
    return csv.DictReader(source)

def email2userpk(data):
    """return mapping to enable user_pk lookup by email.
    Assumes 'data' to hold the 'auth.user' data"""
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
        
