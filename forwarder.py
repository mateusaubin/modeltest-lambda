import json
import logging
import aws

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def process_failed_record(record, source_requestid):

    payload = json.loads(record['Message'])
    payload['jmodeltestrunid'] = record['Subject']
    payload['sourcerequestid'] = source_requestid
    logging.info(json.dumps(payload))

    jobdef = os.getenv('BATCH_JOBDEF')
    jobq = os.getenv('BATCH_JOBQUEUE')

    logging.info("Def: {} | Queue: {}".format(jobdef, jobq))

    assert jobdef, "Job Definition not found, unable to proceed with job submission"
    assert jobq, "Job Queue not found, unable to proceed with job submission"

    batch_result = aws.Batch(jobdef, jobq, payload)

    return batch_result.jobId


def process_sns_record(record):

    sourcetopic = os.getenv('MODELTEST_DLQTOPIC')

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


def execute(event, context):
    aws.SilenceBoto()

    logging.critical('Received Event: {}'.format(json.dumps(event)))

    results = []

    for record in event['Records']:

        submitted_jobs = process_sns_record(record['Sns'])

        results.extend(submitted_jobs)

    logging.warn("Jobs Submitted: {}".format(results))

    return 0



# ------- CUT HERE -------

import os

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
