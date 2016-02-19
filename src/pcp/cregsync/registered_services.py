#
# registered_services.py
#
# script to be invoked via
#
#  cd <your-buildout-root-dir>
#  bin/instance run src/pcp.cregsync/src/pcp/cregsync/registered_services.py
#
#  run with --help to see available options

import logging
from Products.PlonePAS.utils import cleanId
from pcp.cregsync import utils
from pcp.cregsync import config


def prepareid(id):
    return cleanId(id)

def preparedata(values, site, additional_org, email2puid):

    logger = logging.getLogger('cregsync.regservcedata')

    fields = {}
    for k,v in values.items():
        key = k.lower()
        fields[key] = v

    title = fields['name'].encode('utf8').replace('_',' ')
    additional = []
    additional.append({'key': 'creg_id',
                       'value': str(fields['id']),
                       },
                      )
    additional.append({'key': 'email',
                       'value': str(fields['email']),
                       },
                      )

    del fields['id']
    fields['title'] = title
    fields['additional'] = utils.extend(additional_org, additional)
    email = config.creg2dp_email.get(fields['email'].lower(), fields['email'])
    contact_uid = email2puid.get(email.lower(), None)
#    if contact_uid is None:
#        contact_uid = utils.fixContact(site, fields, contact_type='support')
    if contact_uid is None:
        logger.warning("No contact with email address '%s' found." % fields['email'])
    else:
        fields['contact'] = contact_uid
    return fields.copy()

def main(app):
    argparser = utils.getArgParser()
    logger = utils.getLogger('var/log/cregsync_registered_services.log')
    args = argparser.parse_args()
    logger.info("'registered_services.py' called with '%s'" % args)

    site = utils.getSite(app, args.site_id, args.admin_id)
    logger.info("Got site '%s' as '%s'" % (args.site_id, args.admin_id))

    targetfolder = site.operations
    creg_services = utils.getData(args.path, args.filename)   # returns a csv.DictReader instance
    email2puid = utils.email2puid(site)
        
    logger.info("Iterating over the registered services data")
    for entry in creg_services:
        id = prepareid(entry['NAME'])
        if id is None:
            logger.warning("Couldn't generate id for ", values)
            continue
        if id not in targetfolder.objectIds():
            targetfolder.invokeFactory('RegisteredService', id)
            logger.info("Added %s to the operations folder" % id)

        # retrieve data to extended rather than overwritten
        additional = targetfolder[id].getAdditional()
        data = preparedata(entry, site, additional, email2puid)
        logger.debug(data)
        targetfolder[id].edit(**data)
        targetfolder[id].reindexObject()
        logger.info("Updated %s in the operations folder" % id)

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
