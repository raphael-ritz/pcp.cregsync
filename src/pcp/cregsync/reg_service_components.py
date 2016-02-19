#
# reg_service_components.py
#
# script to be invoked via
#
#  cd <your-buildout-root-dir>
#  bin/instance run src/pcp.cregsync/src/pcp/cregsync/reg_service_components.py
#
#  run with --help to see available options

import logging
from Products.PlonePAS.utils import cleanId
from pcp.cregsync import utils
from pcp.cregsync import config


def prepareid(id):
    return cleanId(id)

def getTargetFolder(site, entry):
    """Look up the parent provider from the creg_id"""
    parent_cid = entry['PARENTSITE_ID']
    provider_id = config.cid2dpid[int(parent_cid)]
    try:
        provider = site['providers'][provider_id]
    except:
        logger = logging.getLogger('cregsync.servicedata')
        logger.warning("'%s' not found" % provider_id)
        provider = None
    return provider

def preparedata(values, site, additional_org, extensions, email2puid):

    logger = logging.getLogger('cregsync.servicedata')

    fields = {}
    for k,v in values.items():
        k = k.lower()
        key = config.servicekeys2dp.get(k,k)
        fields[key] = v

    logger.debug(fields)
    title = fields['host_name'].encode('utf8')
    additional = []
    additional.append({'key': 'creg_id',
                       'value': str(fields['id']),
                       },
                      )
    additional.append({'key': 'email',
                       'value': str(fields['email']),
                       },
                      )
    additional.append({'key': 'servicetype_id',
                       'value': str(fields['servicetype_id']),
                       },
                      )

    del fields['id']
    core_additionals = utils.extend(additional_org, additional)
    fields['additional'] = utils.extend(core_additionals, extensions)
    fields['service_type'] = str(fields['servicetype_id'])
    service_type_title = utils.getSTT(fields['servicetype_id'], site)
    fields['title'] = ' - '.join([title, service_type_title])
    email = config.creg2dp_email.get(fields['email'], fields['email'])
    contact_uid = email2puid.get(email, None)
    if contact_uid is None:
        contact_uid = utils.fixContact(site, fields, contact_type='support')
    if contact_uid is None:
        logger.warning("No contact with email address '%s' found." % fields['email'])
    else:
        fields['contacts'] = [contact_uid]

    return fields.copy()

def main(app):
    argparser = utils.getArgParser()
    logger = utils.getLogger('var/log/cregsync_reg_service_components.log')
    args = argparser.parse_args()
    logger.info("'reg_service_components.py' called with '%s'" % args)

    site = utils.getSite(app, args.site_id, args.admin_id)
    logger.info("Got site '%s' as '%s'" % (args.site_id, args.admin_id))

    creg_services = utils.getData(args.path, args.filename)   # returns a csv.DictReader instance
    extension_properties = utils.getProperties(args.path, 'SERVICE_PROPERTIES_DATA_TABLE.csv')
    email2puid = utils.email2puid(site)

    logger.info("Iterating over the service data")
    for entry in creg_services:
        id = prepareid('_'.join([entry['HOSTNAME'], entry['ID']]))
        if id is None:
            logger.warning("Couldn't generate id for ", entry)
            continue
        targetfolder = getTargetFolder(site, entry)
        if targetfolder is None:
            continue
        if id not in targetfolder.objectIds():
            targetfolder.invokeFactory('RegisteredServiceComponent', id)
            logger.info("Added '%s' to '%s'" % (id, targetfolder.Title()))

        # retrieve data to extended rather than overwritten
        additional = targetfolder[id].getAdditional()
        extensions = extension_properties.get(entry['ID'], [])
        data = preparedata(entry, site, additional, extensions, email2puid)
        logger.debug(data)
        targetfolder[id].edit(**data)
        targetfolder[id].reindexObject()
        logger.info("Updated '%s' in '%s'" % (id, targetfolder.Title()))

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
