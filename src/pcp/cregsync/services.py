#
# services.py
#
# script to be invoked via
#
#  cd <your-buildout-root-dir>
#  bin/instance run src/pcp.cregsync/src/pcp/cregsync/services.py
#
#  run with --help to see available options

import logging
from Products.PlonePAS.utils import cleanId
from pcp.cregsync import utils
from pcp.cregsync import config


def prepareid(id):
    return cleanId(id)

def preparedata(values, site, additional_org, email2puid):

    logger = logging.getLogger('cregsync.servicedata')

    fields = {}
    for k,v in values.items():
        fields[k] = v

    title = fields['name'].encode('utf8')
    scl = fields['service_complete_link']['related']['href']
    identifiers = [{'type':'spmt_uid',
                    'value': fields['uuid']},
                    ]

    fields['title'] = title
    fields['description'] = fields['description_external']
    fields['service_complete_link'] = scl
    fields['identifiers'] = identifiers
    # link contacts
    # first map exceptions
    contact_email = fields['contact_information']['email']
    email = config.creg2dp_email.get(contact_email,contact_email)
    # then look up corresponding UID
    contact_uid = email2puid.get(email, None)
#    if contact_uid is None:
#        fields['email'] = contact_email
#        contact_uid = utils.fixContact(site, fields)
    if contact_uid is None:
        logger.warning("'%s' not found - no contact set for '%s'" \
                       % (contact_email, title))
    else:
        fields['contact'] = contact_uid
    # same for the service owner
    owner_email = fields['service_owner']['email']
    o_email = config.creg2dp_email.get(owner_email,owner_email)
    owner_uid = email2puid.get(o_email, None)
#    if owner_uid is None:
#        owner_uid = utils.fixContact(site, fields, contact_type='security')
    if owner_uid is None:
        logger.warning("'%s' not found - no service owner set for '%s'" \
                       % (owner_email, title))
    else:
        fields['service_owner'] = owner_uid
        
    return fields.copy()

def flattenlinks(data):
    """Unpack and inline the embedded links"""
    for field in config.link_fields:
        link = data[field]['related']['href']
        data[field] = link
    details_link = data['service_details']['links']['self']
    data['service_details']['links'] = details_link
    return data

def resolveDependencies(site, data):
    """Resolve dependencies by looking up the UIDs of the respective
    services. It is assumed that the services are there and can be
    looked up by name in the 'catalog' folder."""
    deps = data['dependencies']['services']
    if not deps:
        data['dependencies'] = []
    else:
        dependencies = []
        for dep in deps:
            name = dep['service']['name']
            uid = site['catalog'][name].UID()
            dependencies.append(uid)
        data['dependencies'] = dependencies
    return data

def addDetails(site, parent, data, logger):
    """Adding service details"""
    if not 'details' in parent.objectIds():
        parent.invokeFactory('Service Details', 'details')
        logger.info("Adding 'details' to '%s'" % parent.getId())
    details = parent.details
    data = flattenlinks(data)
    data = resolveDependencies(site, data)
    data['identifiers'] = [{'type':'spmt_uid',
                            'value': data['uuid']},
                       ]
    details.edit(**data)
    details.reindexObject()
    site.portal_repository.save(obj=details, 
                                comment="Synchronization from SPMT")
    logger.info("Updated 'details' of '%s'" % parent.getId())
    

def main(app):
    argparser = utils.getArgParser()
    logger = utils.getLogger('var/log/cregsync_services.log')
    args = argparser.parse_args()
    logger.info("'services.py' called with '%s'" % args)

    site = utils.getSite(app, args.site_id, args.admin_id)
    logger.info("Got site '%s' as '%s'" % (args.site_id, args.admin_id))

    targetfolder = site.catalog
    # returns a list of dicts with service data
    spmt_services = utils.getServiceData(args.path, args.filename)   
    email2puid = utils.email2puid(site)
        
    logger.info("Iterating over the service data")
    for entry in spmt_services:
        shortname = entry['name']
        id = prepareid(shortname)
        if id is None:
            logger.warning("Couldn't generate id for ", values)
            continue
        if id not in targetfolder.objectIds():
            targetfolder.invokeFactory('Service', id)
            logger.info("Added %s to the 'catalog' folder" % id)

        # retrieve data to extended rather than overwrite
        additional = targetfolder[id].getAdditional()
        data = preparedata(entry, site, additional, email2puid)
        logger.debug(data)
        targetfolder[id].edit(**data)
        targetfolder[id].reindexObject()
        site.portal_repository.save(obj=targetfolder[id], 
                                    comment="Synchronization from SPMT")
        logger.info("Updated %s in the 'catalog' folder" % id)
        try:
            data = entry['service_details_list']['service_details'][0]  
            # we assume there is at most one
            addDetails(site, targetfolder[id], data, logger)
        except IndexError:
            pass

    if not args.dry:
        logger.info("Committing changes to database")
        import transaction
        transaction.commit()
    else:
        logger.info("dry run; not committing anything")
            
    logger.info("Done")

# As this script lives in your source tree, we need to use this trick so that
# five.grok, which scans all modules, does not try to execute the script while
# modules are being loaded on start-up
if "app" in locals():
    main(app)
