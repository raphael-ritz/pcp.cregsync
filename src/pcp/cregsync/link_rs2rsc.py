#
# link_rs2rsc.py
#
# script to be invoked via
#
#  cd <your-buildout-root-dir>
#  bin/instance run src/pcp.cregsync/src/pcp/cregsync/link_rs2rsc.py
#
#  run with --help to see available options

import logging
from Products.PlonePAS.utils import cleanId
from pcp.cregsync import utils
from pcp.cregsync import config


def main(app):
    argparser = utils.getArgParser()
    logger = utils.getLogger('var/log/cregsync_link_rs2rsc.log')
    args = argparser.parse_args()
    logger.info("'link_rs2rsc.py' called with '%s'" % args)

    site = utils.getSite(app, args.site_id, args.admin_id)
    logger.info("Got site '%s' as '%s'" % (args.site_id, args.admin_id))

    creg_links = utils.getData(args.path, args.filename)   # returns a csv.DictReader instance
    link_data = utils.prepare_links(creg_links, site)   # returns a dict; keys are RS uids, values RSC uids
    catalog = site.portal_catalog
        
    logger.info("Iterating over the link data")

    for k, v in link_data.items():
        search = catalog(UID=k)
        rs = search[0].getObject()
        logger.info("Linking '%s' to '%s'" % (rs.Title(),v))
        rs.setService_components(v)
        rs.reindexObject()

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
