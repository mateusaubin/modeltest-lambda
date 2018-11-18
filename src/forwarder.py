import os
import sys
import json
import logging


# FIX CRAZY BEHAVIOR IN LAMBDA WITH IMPORTS
CWD = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, CWD)
import aws


logger = logging.getLogger()
logger.setLevel(logging.INFO)

env = None
jobdef = os.getenv('BATCH_JOBDEF')
jobq = os.getenv('BATCH_JOBQUEUE')
jobcomp = os.getenv('BATCH_COMPUTE')
sourcetopic = os.getenv('MODELTEST_DLQTOPIC')

def GatherEnvVars():
    global env

    assert jobdef, "Job Definition not found, unable to proceed with job submission"
    assert jobq, "Job Queue not found, unable to proceed with job submission"

    env = {
        'JobDefinition': jobdef,
        'JobQueue':      jobq,
        'SourceTopic':   sourcetopic
    }


def process_failed_record(record, source_requestid):

    payload = json.loads(record['Message'])
    payload['jmodeltestrunid'] = record['Subject']
    payload['sourcerequestid'] = source_requestid
    logging.info(json.dumps(payload))

    batch_result = aws.Batch(jobdef, jobq, payload)

    info = {key: value for (key, value) in (list(payload.items()) + list(env.items()))}
    logging.warning("Submitted Batch Job: {}".format(json.dumps(info)))

    return batch_result.jobId


def process_sns_record(record):

    topic_arn = record['TopicArn']
    error_message = record['MessageAttributes']['ErrorMessage']['Value']
    source_requestid = record['MessageAttributes']['RequestID']['Value']

    logging.info("Lambda RequestId: {}".format(source_requestid))

    assert sourcetopic in topic_arn, "Message came from unknown topic: {}".format(topic_arn)
    assert "Task timed out" in error_message, "Expected timeout, got '{}'".format(error_message)

    event_msg = json.loads(record['Message'])
    results = []

    for failed in event_msg['Records']:

        submitted_job = process_failed_record(failed['Sns'], source_requestid)

        results.append(submitted_job)

    return results


def trigger_compute():
    try:
        aws.Batch.TriggerCompute(jobcomp)
    except:
        pass


def execute(event, context):
    aws.SilenceBoto()
    
    logging.debug('Received Event: {}'.format(json.dumps(event)))

    GatherEnvVars()

    results = []

    for record in event['Records']:

        submitted_jobs = process_sns_record(record['Sns'])

        results.extend(submitted_jobs)

    trigger_compute()

    logging.info("Jobs Submitted: {}".format(results))

    return 0



# ------- CUT HERE -------


if bool(os.getenv('IS_LOCAL', False)) & bool(os.getenv('VSCODE', False)):
    # log setup
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)-8s | %(message)s")

    # feed event file
    with open(os.getenv('DEBUG_FILE')) as f:
        contents = f.read()
        data = json.loads(contents)

    logging.warning("Local Debugger Session")
    execute(data, None)
    logging.warning("Execution Ended")
