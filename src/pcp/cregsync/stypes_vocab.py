#
# stypes_vocab.py
#
# script to be invoked via
#
#  cd <your-buildout-root-dir>
#  bin/instance run src/pcp.cregsync/src/pcp/cregsync/stypes_vocab.py
#
#  run with --help to see available options
#
#  Generates controlled vocabulary for the creg:service types
#

import logging
from pcp.cregsync import utils


def main(app):
    argparser = utils.getArgParser()
    logger = utils.getLogger('var/log/cregsync_stypes.log')
    args = argparser.parse_args()
    logger.info("'stypes_vocab.py' called with '%s'" % args)

    site = utils.getSite(app, args.site_id, args.admin_id)
    logger.info("Got site '%s' as '%s'" % (args.site_id, args.admin_id))

    # sneak in default filename if not given
    filename = args.filename
    if not filename:
        filename = "SERVICETYPES_DATA_TABLE.csv"

    tool = site.portal_vocabularies
    creg_types = utils.getData(args.path, filename)   # returns a csv.DictReader instance

    # make sure the vocab exists
    vocab_id = 'service_types'
    if vocab_id not in tool.objectIds():
        tool.invokeFactory('SimpleVocabulary', 
                           vocab_id, 
                           title='Service Types for Registered Service Components'
        )
    targetfolder = tool[vocab_id]

    logger.info("Iterating over the service types data")
    for entry in creg_types:
        id = entry['ID']
        if id not in targetfolder.objectIds():
            targetfolder.invokeFactory('SimpleVocabularyTerm', id)
            logger.info("Added '%s' to the service types vocablary" % id)
        data = {'title':entry['NAME'],
                'description':entry['DESCRIPTION']}
        logger.debug(data)
        targetfolder[id].edit(**data)
        logger.info("Updated '%s' in the service types vocabulary" % id)

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
