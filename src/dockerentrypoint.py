import os
import sys
import json
import logging

import modeltest


logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)
logger = logging.getLogger()


filepath         = sys.argv[1]
commandlineargs  = sys.argv[2]
jmodeltestrunid  = sys.argv[3]
source_requestid = None if sys.argv[4] == 'None' else sys.argv[4]


assert '://' in filepath and filepath.endswith('.phy'), "Filepath not recognized"
assert '--run_id' in commandlineargs and '--no_memory_check' in commandlineargs, "Commandline doesn't look like it belongs to PhyML"
assert jmodeltestrunid, "Runid mustn't be blank"


info = { 
    'JobId':        os.getenv("AWS_BATCH_JOB_ID", None), 
    'AttemptNo':    os.getenv("AWS_BATCH_JOB_ATTEMPT", -1),
    'FilePath':     filepath,
    'CmdArgs':      commandlineargs,
    'jModelRunId':  jmodeltestrunid,
    'SrcRequestId': source_requestid
}
logger.info("Started Docker: {}".format(json.dumps(info)))


#cwd = os.getcwd()
# logger.critical("CWD={}".format(cwd))
#
#retry = os.getenv("AWS_BATCH_JOB_ATTEMPT", -1)
# logger.info("Retry={}".format(retry))


# build args
context_obj = modeltest.Context()
event_obj = {
    'Records': [{
        'Sns': {
            'Subject': jmodeltestrunid,
            'Message': json.dumps({'path': filepath, 'cmd': commandlineargs})
        }
    }]
}
if source_requestid:
    event_obj['SourceRequestId'] = source_requestid

logger.debug(json.dumps(event_obj))

from timeit import default_timer as timer
start = timer()

# reuse lambda function
modeltest.execute(event_obj, context_obj)

duration = (timer() - start)
duration = int(duration * 1000)

logger.critical("REPORT RequestId: {} Duration: {} ms".format(
    context_obj.aws_request_id, duration))
