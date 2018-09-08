import os
import json
import aws
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
#libdir = os.path.join(os.getcwd(), 'lib', 'phyml')


def execute(event, context):
    #result = subprocess.run([libdir, "--help"], stdout=subprocess.PIPE)
    # return {
    #    'result': "%s" % result.stdout
    # }
    #import subprocess
    # command = ["./aws", "s3", "sync", "--acl", "public-read", "--delete",
    #           source_dir + "/", "s3://" + to_bucket + "/"]
    #print(subprocess.check_output(command, stderr=subprocess.STDOUT))

    logging.debug('Received Event: {}'.format(event))

    for record in event['Records']:
        sns = aws.SNSInterface(record)
        sns.download()

    return 0


if bool(os.getenv('IS_LOCAL', False)) & bool(os.getenv('VSCODE', False)):
    # log setup
    logging.basicConfig(level=logging.INFO,
                        format="  %(levelname)-8s | %(message)s")

    # feed event file
    with open(os.getenv('DEBUG_FILE')) as f:
        data = json.load(f)
        logging.warning("Local Debugger Session")
        execute(data, None)
        logging.warning("Execution Ended")
