import boto3
import json
import os
from pathlib import Path
import shutil
import logging

correlation_id = None


class SNS:

    def __init__(self, sns_message):
        logging.debug('Processing Message: {}'.format(sns_message))
        self.file_info = self.__parse(sns_message)

    def __parse(self, sns_message):
        phyml_params = json.loads(sns_message)
        filedata = phyml_params.pop('path').split('://')

        logging.info("Received Payload: {}".format(phyml_params))
        self.payload = phyml_params['cmd']
        self.jmodel_runid = self.payload.split('--run_id ')[1].split()[0]

        return {'bucket': filedata[0], 'key': filedata[1]}


class S3Download:

    def __init__(self, finfo):
        self.__file_info = finfo
        self.__parse_paths(finfo)

        if os.path.exists(self.local_file):
            logging.debug("File already exists {}".format(self.local_file))
        else:
            logging.info("Downloading to: {}".format(self.local_file))
            self.s3 = boto3.client('s3')
            self.__download(self.__file_info)

    def __parse_paths(self, finfo):
        self.tmp_folder = os.path.join('/tmp', correlation_id)
        self.local_file = os.path.join(
            '/tmp', correlation_id, "_input")

    def __download(self, file_info):
        os.mkdir(self.tmp_folder)
        self.s3.download_file(
            file_info['bucket'], file_info['key'], self.local_file)
