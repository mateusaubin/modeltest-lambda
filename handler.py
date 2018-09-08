import os
import json
import aws
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

import subprocess


def execute(event, context):
    #result = subprocess.run([libdir, "--help"], stdout=subprocess.PIPE)
    # return {
    #    'result': "%s" % result.stdout
    # }
    #import subprocess

    logging.debug('Received Event: {}'.format(event))

    for record in event['Records']:
        sns = aws.SNSInterface(record)
        sns.download()

        cmdline_args = [os.path.join(os.getcwd(), 'lib', 'phyml')]
        [cmdline_args.extend([k, v]) for k, v in sns.payload.items() if v != None]
        cmdline_args.extend(k for k, v in sns.payload.items() if v == None)

        with open( os.path.join(sns.tmp_folder, "trace.log"), "w") as file:
            result = subprocess.run(cmdline_args,
                                    stdout=file,
                                    stderr=subprocess.STDOUT)

        logging.warn(result)

        logging.info(os.listdir(sns.tmp_folder))
        logging.info(subprocess.run(["cat", os.path.join(sns.tmp_folder, "trace.log")], stdout=subprocess.PIPE))

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
