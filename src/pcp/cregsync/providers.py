#
# providers.py
#
# script to be invoked via
#
#  cd <your-buildout-root-dir>
#  bin/instance run src/pcp.cregsync/src/pcp/cregsync/providers.py
#
#  run with --help to see available options

import logging
from Products.PlonePAS.utils import cleanId
from pcp.cregsync import utils
from pcp.cregsync import config


def prepareid(id):
    return cleanId(id)

def preparedata(values, site, additional_org):

    logger = logging.getLogger('cregsync.providerdata')

    fields = {}
    for k,v in values.items():
        k = k.lower()
        key = config.sitekeys2dp.get(k,k)
        fields[key] = v

    title = fields['shortname'].encode('utf8')
    additional = []
    additional.append({'key': 'creg_id',
                       'value': str(fields['id']),
                       },
                      )
    additional.append({'key': 'creg_pk',
                       'value': str(fields['primarykey']),
                       },
                      )

    del fields['id']
    fields['title'] = title
    fields['additional'] = utils.extend(additional_org, additional)

    return fields.copy()

def main(app):
    argparser = utils.getArgParser()
    logger = utils.getLogger('var/log/cregsync_providers.log')
    args = argparser.parse_args()
    logger.info("'providers.py' called with '%s'" % args)

    site = utils.getSite(app, args.site_id, args.admin_id)
    logger.info("Got site '%s' as '%s'" % (args.site_id, args.admin_id))

    targetfolder = site.providers
    creg_sites = utils.getData(args.path, args.filename)   # returns a csv.DictReader instance

        
    logger.info("Iterating over the provider data")
    for entry in creg_sites:
        id = prepareid(entry['SHORTNAME'])
        if id is None:
            logger.warning("Couldn't generate id for ", values)
            continue
        if id not in targetfolder.objectIds():
            targetfolder.invokeFactory('Provider', id)
            logger.info("Added %s to the providers folder" % id)

        # retrieve data to extended rather than overwritten
        additional = targetfolder[id].getAdditional()
        data = preparedata(entry, site, additional)
        logger.debug(data)
        targetfolder[id].edit(**data)
        targetfolder[id].reindexObject()
        logger.info("Updated %s in the providers folder" % id)

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
