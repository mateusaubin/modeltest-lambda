import boto3
import json
import os
from pathlib import Path
import shutil
import logging

# aws request id 
correlation_id = None

# 'globally declared' for caching
s3_client = boto3.client('s3')


class SNS:

    def __init__(self, sns_message):
        logging.debug('Processing Message: {}'.format(json.dumps(sns_message['Message'])))
        self.file_info = self.__parse(sns_message)

    def __parse(self, sns_message):
        phyml_params = json.loads(sns_message['Message'])
        filedata = phyml_params.pop('path').split('://')

        logging.info("Received Payload: {}".format(phyml_params))

        self.payload = phyml_params['cmd']
        self.jmodel_modelname = self.payload.split('--run_id ')[1].split()[0]
        self.jmodel_runid = sns_message['Subject']

        return {'bucket': filedata[0], 'key': filedata[1]}


class S3Download:

    def __init__(self, finfo):
        self.__file_info = finfo
        self.__parse_paths(finfo)

        if os.path.exists(self.local_file):
            logging.warn("File already exists {}".format(self.local_file))
        else:
            logging.info("Downloading to: {}".format(self.local_file))
            self.__download(self.__file_info)

    def __parse_paths(self, finfo):
        self.tmp_folder = os.path.join('/tmp', correlation_id)
        self.local_file = os.path.join(
            '/tmp', correlation_id, "_input")

    def __download(self, file_info):
        os.makedirs(self.tmp_folder, exist_ok=True)
        logging.info(file_info)
        s3_client.download_file(
            file_info['bucket'], file_info['key'], self.local_file)


class S3Upload:
    
    NEEDED_FILES = ['trace','tree','stats']


    def __init__(self, tmp_folder, files, sns_result):

        # sanity check
        for string in files:
            assert(any(substring in string for substring in self.NEEDED_FILES))

        # save needed information
        self.tmp_folder = tmp_folder
        self.src_bucket = sns_result.file_info['bucket']
        self.jmodel_modelname = sns_result.jmodel_modelname
        self.jmodel_runid = sns_result.jmodel_runid

        # parse/fix filenames
        self.files = {x : self.__FixPhymlTraceFilenames(x) for x in files}

        # send to s3
        self.uploaded_files = self.__upload()
    
    def __upload(self):

        uploaded = []

        for phyml_original_filename, fixed_filename in self.files.items():

            src_file = os.path.join(self.tmp_folder, phyml_original_filename)
            dst_file = "/".join([self.jmodel_runid, fixed_filename])

            s3_client.upload_file(
                src_file,
                self.src_bucket,
                dst_file,
                ExtraArgs={
                    'ContentType': 'text/plain',
                    'ContentDisposition': phyml_original_filename
                }
            )

            uploaded.append(dst_file)
        
        return uploaded

    def __FixPhymlTraceFilenames(self, filename):

        remove_redundant = filename.replace("_input_phyml_","")
        remove_extension = remove_redundant[:-4]

        # make sure to keep Model identifier
        assert(self.jmodel_modelname in remove_extension)
        
        reverse = reversed(remove_extension.split("_"))
        result = ("_".join(reverse)) + ".txt"
        
        return result
