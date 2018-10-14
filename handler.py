import os
import json
import aws
import logging
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

import subprocess


def execute(event, context):
    aws.SilenceBoto()

    logging.debug('Received Event: {}'.format(event))

    aws.correlation_id = event.get('SourceRequestId', context.aws_request_id)
    logging.info("Lambda RequestId: {}".format(aws.correlation_id))

    for record in event['Records']:

        logging.info("Subject: {}".format(record['Sns']['Subject']))

        sns_result = aws.SNS(record['Sns'])
        s3_result = aws.S3Download(sns_result.file_info)

        cmdline_args = [os.path.join(os.getcwd(), 'lib', 'phyml'), ]
        cmdline_args.extend(['-i', s3_result.local_file])
        cmdline_args.extend(sns_result.payload.split())

        trace_file = os.path.join(
            s3_result.tmp_folder,
            "_input_phyml_trace_{}.txt".format(sns_result.jmodel_modelname)
        )

        with open(trace_file, "w") as file:
            result = subprocess.run(cmdline_args,
                                    stdout=file,
                                    stderr=subprocess.STDOUT)

        # bail out if phyml error'd
        if result.returncode != 0:

            logging.critical("PhyML.ReturnCode={}".format(result.returncode))

            # log trace file
            with open(trace_file, 'r', encoding='UTF-8') as file_stream:
                file_contents = file_stream.read()
                logging.error(file_contents)

            raise subprocess.SubprocessError("Error calling PhyML")

        # phyml succeeded, go ahead

        result_files = [x for x in os.listdir(
            s3_result.tmp_folder) if x != "_input"]

        logging.warn("Phyml produced = {}".format(result_files))

        s3_up = aws.S3Upload(s3_result.tmp_folder, result_files, sns_result)

        logging.info("Uploaded = {} to {}://{}/".format(
            list(s3_up.files.values()),
            sns_result.file_info['bucket'],
            s3_up.jmodel_runid)
        )

    return 0


# ------- CUT HERE -------

class Context(object):
    def __init__(self):
        self.aws_request_id = str(uuid.uuid4())


if __name__ == '__main__':
    if bool(os.getenv('IS_LOCAL', False)) & bool(os.getenv('VSCODE', False)):
        # log setup
        logging.basicConfig(level=logging.INFO,
                            format="%(levelname)-8s | %(message)s")

        # context mock
        context = Context()

        # feed event file
        with open(os.getenv('DEBUG_FILE')) as f:
            contents = f.read().replace(
                '{{message-subject}}', 
                context.aws_request_id
            )
            data = json.loads(contents)

        logging.warning("Local Debugger Session")
        execute(data, context)
        logging.warning("Execution Ended")

        import shutil
        shutil.rmtree('/tmp/'+context.aws_request_id)
