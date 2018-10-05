import json
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

aws_batch_cli = boto3.client('batch')

def execute(event, context):
    logging.info('Received Event: {}'.format(json.dumps(event)))

    response = aws_batch_cli.submit_job(
                    jobName='forwardedFromLambda', # use your HutchNet ID instead of 'jdoe'
                    jobDefinition='modeltest-batch-jobdef:14', # use a real job definition
                    jobQueue='modeltest-batch-queue', # sufficient for most jobs
                    parameters={ "phyfilepath" : "small" }
                    #containerOverrides={
                    #    "environment": [ # optionally set environment variables
                    #        {"name": "FAVORITE_COLOR", "value": "blue"},
                    #        {"name": "FAVORITE_MONTH", "value": "December"}
                    #    ]
                    #}
                    )

    logging.warn("Job ID is {}.".format(response['jobId']))
