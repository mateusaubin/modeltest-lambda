import os
import json
import aws
import logging
import uuid

logger = logging.getLogger()
logger.setLevel(logging.WARNING)

import subprocess


def execute(event, context):
    logging.debug('Received Event: {}'.format(event))

    aws.correlation_id = context.aws_request_id

    for record in event['Records']:

        logging.warning("Subject: {}".format(record['Sns']['Subject']))
        
        sns_result = aws.SNS(record['Sns'])
        s3_result = aws.S3Download(sns_result.file_info)

        cmdline_args = [os.path.join(os.getcwd(), 'lib', 'phyml'), ]
        cmdline_args.extend(['-i', s3_result.local_file])
        cmdline_args.extend(sns_result.payload.split())

        trace_file = os.path.join(
            s3_result.tmp_folder,
            "_input_phyml_trace_{}.log".format(sns_result.jmodel_modelname)
        )

        with open(trace_file, "w") as file:
            result = subprocess.run(cmdline_args,
                                    stdout=file,
                                    stderr=subprocess.STDOUT)

        logging.warn("PhyML.ReturnCode={}".format(result.returncode))
        resultfiles = [x for x in os.listdir(s3_result.tmp_folder) if x != "_input"]

        whatevs = aws.S3Upload(s3_result.tmp_folder, resultfiles, sns_result)
        #''.join(reversed(tmp.split(',')))
        # debug por enquanto
        logging.warn(resultfiles)

        # bail out if phyml error'd
        # TODO: assert a existência dos 3 arquivos [ {filenamewithext}_phyml_stats_{run_id}, {filenamewithext}_phyml_tree_{run_id}, trace.log ]
        if result.returncode != 0:

            processData = subprocess.run(
                ["cat", trace_file], 
                stdout=subprocess.PIPE
            )
            logging.error(processData.stdout.decode('UTF-8'))
            
            raise subprocess.SubprocessError("Error calling PhyML")

    return 0


class Context(object):
    def __init__(self):
        self.aws_request_id = str(uuid.uuid4())
        

if bool(os.getenv('IS_LOCAL', False)) & bool(os.getenv('VSCODE', False)):
    # log setup
    logging.basicConfig(level=logging.INFO,
                        format="  %(levelname)-8s | %(message)s")

    # context mock
    context = Context()

    # feed event file
    with open(os.getenv('DEBUG_FILE')) as f:
        contents = f.read().replace('{{message-subject}}', context.aws_request_id)
        data = json.loads(contents)

    logging.warning("Local Debugger Session")
    execute(data, context)
    logging.warning("Execution Ended")
