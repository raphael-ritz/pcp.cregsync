import json
import logging
import argparse
from collections import defaultdict

from AccessControl.SecurityManagement import newSecurityManager
from Testing import makerequest

from zope.component.hooks import setSite


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
    

def getData(path, model=None):
    # TODO: this needs to be adjusted for CSV data
    source = open(path,'r')
    raw = json.load(source)
    rct_data = defaultdict(dict)

    # cast the raw data into some nested structure for easy access later
    for item in raw:
        rct_data[item['model']][item['pk']] = item.copy()
    if not model:
        return rct_data.copy()
    else:
        return rct_data[model].copy()

def email2userpk(data):
    """return mapping to enable user_pk lookup by email.
    Assumes 'data' to hold the 'auth.user' data"""
    result = {}
    for pk, values in data.items():
        email = values['fields']['email']
        result[email] = pk
    return result.copy()
