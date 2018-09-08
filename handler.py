import os
import json
import aws
import logging
import uuid

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
        sns = aws.SNSInterface(record, context.aws_request_id)
        sns.download()

        cmdline_args = [os.path.join(os.getcwd(), 'lib', 'phyml')]
        [cmdline_args.extend([k, v])
         for k, v in sns.payload.items() if v != None]
        cmdline_args.extend(k for k, v in sns.payload.items() if v == None)

        with open(os.path.join(sns.tmp_folder, "trace.log"), "w") as file:
            result = subprocess.run(cmdline_args,
                                    stdout=file,
                                    stderr=subprocess.STDOUT)

        logging.warn(result)

        # bail out if phyml error'd
        result.check_returncode()
        # TODO: assert a existência dos 3 arquivos [ {filenamewithext}_phyml_stats_{run_id}, {filenamewithext}_phyml_tree_{run_id}, trace.log ]

        # debug por enquanto
        logging.info(os.listdir(sns.tmp_folder))
        logging.info(subprocess.run(["cat", os.path.join(
            sns.tmp_folder, "trace.log")], stdout=subprocess.PIPE))

    return 0


if bool(os.getenv('IS_LOCAL', False)) & bool(os.getenv('VSCODE', False)):
    # log setup
    logging.basicConfig(level=logging.INFO,
                        format="  %(levelname)-8s | %(message)s")

    # context mock
    class Context(object):
        def __init__(self):
            self.aws_request_id = str(uuid.uuid4())

    # feed event file
    with open(os.getenv('DEBUG_FILE')) as f:
        data = json.load(f)

    logging.warning("Local Debugger Session")
    execute(data, Context())
    logging.warning("Execution Ended")
