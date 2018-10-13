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
    logging.info(payload)

    response = aws_batch_cli.submit_job(
                    jobName='forwardedFromLambda', # use your HutchNet ID instead of 'jdoe'
                    jobDefinition='BatchJobDef-d6100469b297fb9:1', # use a real job definition
                    jobQueue='BatchJobQueue-0127f6efa726a10', # sufficient for most jobs
                    parameters=payload
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
    logging.debug('Received Event: {}'.format(json.dumps(event)))

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
