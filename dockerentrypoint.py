import os
import sys
import json
import logging


import handler

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)
logger = logging.getLogger()



#filepath        = 'mestrado-dev-phyml://#_src/primate-mtDNA.phy'
#commandlineargs = '-d nt -n 1 -b 0 --run_id GTR+I+G -m 012345 -f m -v e -c 4 -a e --no_memory_check --r_seed 12345 -o tlr -s BEST'
#jmodeltestrunid = 'docker'
filepath        = sys.argv[1]
commandlineargs = sys.argv[2]
jmodeltestrunid = sys.argv[3]

assert '://' in filepath and filepath.endswith('.phy'), "Filepath not recognized"
assert '--run_id' in commandlineargs and '--no_memory_check' in commandlineargs, "Commandline doesn't look like it belongs to Phyml"
assert jmodeltestrunid, "Runid mustn't be blank"


cwd = os.getcwd()
logger.critical("CWD={}".format(cwd))

retry = os.getenv("AWS_BATCH_JOB_ATTEMPT", -1)
logger.info("Retry={}".format(retry))


# build args
context_obj = handler.Context()
event_obj = {
    'Records': [{
        'Sns': {
            'Subject': jmodeltestrunid,
            'Message': json.dumps( {'path': filepath, 'cmd': commandlineargs} ) # json payload
        }
    }]
}

logger.info(json.dumps(event_obj))

# reuse lambda function
handler.execute(event_obj, context_obj)

logger.critical("----- THE END -----")