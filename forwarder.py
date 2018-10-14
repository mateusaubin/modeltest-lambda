import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

aws_batch_cli = boto3.client('batch')

def process_failed_record(record):

    # jmodel_runid = Subject
    # json {cmd, path} = Message

    payload = json.loads(record['Message'])
    payload['jmodeltestrunid'] = record['Subject']
    logging.info(json.dumps(payload))

    jobdef = os.getenv('BATCH_JOBDEF')
    jobq = os.getenv('BATCH_JOBQUEUE')

    logging.info("Def: {} | Queue: {}".format(jobdef, jobq))

    assert jobdef, "Job Definition not found, unable to proceed with job submission"
    assert jobq, "Job Queue not found, unable to proceed with job submission"


    response = aws_batch_cli.submit_job(
                    jobName         = 'forwardedFromLambda',
                    jobDefinition   = jobdef,
                    jobQueue        = jobq,
                    parameters      = payload
                    #containerOverrides={
                    #    "environment": [ # optionally set environment variables
                    #        {"name": "FAVORITE_COLOR", "value": "blue"},
                    #        {"name": "FAVORITE_MONTH", "value": "December"}
                    #    ]
                    #}
                )

    logging.debug("Job ID is {}.".format(response['jobId']))

    assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.Submit_Job"

    return response['jobId']

def process_sns_record(record):

    assert "mestrado-dev-failed" in record['TopicArn'], "Message came from unknown topic: {}".format(record['TopicArn'])
    assert "Task timed out" in record['MessageAttributes']['ErrorMessage']['Value'], "Expected timeout, got '{}'".format(record['MessageAttributes']['ErrorMessage']['Value'])

    event_msg = json.loads(record['Message'])
    results = []

    for failed in event_msg['Records']:

        submitted_job = process_failed_record(failed['Sns'])
        
        results.append(submitted_job)


    return results

def execute(event, context):
    logging.critical('Received Event: {}'.format(json.dumps(event)))

    results = []
    
    for record in event['Records']:

        submitted_jobs = process_sns_record(record['Sns'])

        results.extend(submitted_jobs)
    

    logging.warn("Jobs Submitted: {}".format(results))
    


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
