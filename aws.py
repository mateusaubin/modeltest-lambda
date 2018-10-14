import boto3
import json
import os
from pathlib import Path
import shutil
import logging

# aws request id
correlation_id = None
# aws lambda temp
TEMP_FOLDER_PREFIX = '/tmp'

# 'globally declared' for caching
s3_client = boto3.client('s3')
batch_client = boto3.client('batch')


def SilenceBoto():
    BOTO_LEVEL = logging.WARNING
    logging.getLogger('boto').setLevel(BOTO_LEVEL)
    logging.getLogger('boto3').setLevel(BOTO_LEVEL)
    logging.getLogger('botocore').setLevel(BOTO_LEVEL)


class SNS:

    def __init__(self, sns_message):
        logging.debug("Processing Message: {}".format(
            json.dumps(sns_message['Message']))
        )

        assert sns_message['Message'] and sns_message['Subject'], "Malformed SNS Message"

        self.file_info = self.__parse(sns_message)

    def __parse(self, sns_message):

        MODELNAME_TOKEN = "--run_id "
        BUCKETPATH_TOKEN = "://"
        PHYML_EXTENSION = ".phy"

        phyml_params = json.loads(sns_message['Message'])
        logging.info("Received Payload: {}".format(phyml_params))

        filepath = phyml_params.pop('path')

        assert BUCKETPATH_TOKEN in filepath and filepath.endswith(PHYML_EXTENSION), "Filepath not recognized"

        self.payload = phyml_params['cmd']

        assert MODELNAME_TOKEN in self.payload, "Payload doesn't look like it belongs to PhyML"

        self.jmodel_modelname = self.payload.split(MODELNAME_TOKEN)[1].split()[0]
        self.jmodel_runid = sns_message['Subject']
        filedata = filepath.split('://')

        return {'bucket': filedata[0], 'key': filedata[1]}


class S3Download:

    def __init__(self, finfo):
        self.__file_info = finfo
        self.__generate_temp_paths()

        if os.path.exists(self.local_file):
            logging.warn("File already exists {}".format(self.local_file))
        else:
            logging.info("Downloading to: {}".format(self.local_file))
            self.__download()

    def __generate_temp_paths(self):
        self.tmp_folder = os.path.join(
            TEMP_FOLDER_PREFIX, 
            correlation_id
        )
        self.local_file = os.path.join(
            TEMP_FOLDER_PREFIX, 
            correlation_id, 
            "_input"
        )

    def __download(self):
        os.makedirs(self.tmp_folder, exist_ok=True)
        logging.info(self.__file_info)
        s3_client.download_file(
            self.__file_info['bucket'],
            self.__file_info['key'],
            self.local_file
        )


class S3Upload:

    NEEDED_FILES = ['trace', 'tree', 'stats']

    def __init__(self, tmp_folder, files, sns_result):

        # sanity check
        for string in files:
            assert any(
                substring in string for substring in self.NEEDED_FILES
            ), "Missing expected output files from Phyml"

        # save needed information
        self.__tmp_folder = tmp_folder
        self.__src_bucket = sns_result.file_info['bucket']
        self.__jmodel_modelname = sns_result.jmodel_modelname
        self.jmodel_runid = sns_result.jmodel_runid

        # parse/fix filenames
        self.files = {x: self.__FixPhymlTraceFilenames(x) for x in files}

        # send to s3
        self.uploaded_files = self.__upload()

    def __upload(self):

        uploaded = []

        for phyml_original_filename, fixed_filename in self.files.items():

            src_file = os.path.join(self.__tmp_folder, phyml_original_filename)
            dst_file = os.path.join(self.jmodel_runid, fixed_filename)

            s3_client.upload_file(
                src_file,
                self.__src_bucket,
                dst_file,
                ExtraArgs={
                    'ContentType': "text/plain",
                    'ContentDisposition': phyml_original_filename
                }
            )

            uploaded.append(dst_file)

        return uploaded

    def __FixPhymlTraceFilenames(self, filename):

        remove_redundant = filename.replace("_input_phyml_", "")
        remove_extension = remove_redundant[:-4]

        # make sure to keep Model identifier
        assert self.__jmodel_modelname in remove_extension, "Fixed filename lost Model name"

        reverse = reversed(remove_extension.split("_"))
        result = ("_".join(reverse)) + ".txt"

        return result


class Batch:
    def __init__(self, jobdef, jobq, payload):
        response = batch_client.submit_job(
            jobName       = 'forwardedFromLambda',
            jobDefinition = jobdef,
            jobQueue      = jobq,
            parameters    = payload
            #containerOverrides={
            #    "environment": [ # optionally set environment variables
            #        {"name": "FAVORITE_COLOR", "value": "blue"},
            #        {"name": "FAVORITE_MONTH", "value": "December"}
            #    ]
            #}
        )

        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.Submit_Job"
        assert response['jobId'], "Empty JobId"

        logging.debug("Job ID is {}.".format(response['jobId']))

        self.jobId = response['jobId']
