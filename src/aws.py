import boto3
import json
import os
import math
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
dynamo_client = boto3.client('dynamodb')


def SilenceBoto():
    BOTO_LEVEL = logging.WARNING
    
    logging.getLogger('nose').setLevel(BOTO_LEVEL)
    logging.getLogger('boto3').setLevel(BOTO_LEVEL)
    logging.getLogger('urllib3').setLevel(BOTO_LEVEL)
    logging.getLogger('botocore').setLevel(BOTO_LEVEL)
    logging.getLogger('s3transfer').setLevel(BOTO_LEVEL)


class SNS:

    def __init__(self, sns_message):
        assert sns_message['Message'] and sns_message['Subject'], "Malformed SNS Message"

        self.file_info = self.__parse(sns_message)

    def __parse(self, sns_message):

        MODELNAME_TOKEN = "--run_id "
        BUCKETPATH_TOKEN = "://"
        PHYML_EXTENSION = ".phy"

        phyml_params = json.loads(sns_message['Message'])
        logging.info("Received Payload: {}".format(json.dumps(phyml_params)))

        filepath = phyml_params.pop('path')

        assert BUCKETPATH_TOKEN in filepath and filepath.endswith(PHYML_EXTENSION), "Filepath not recognized"

        self.payload = phyml_params['cmd']

        assert MODELNAME_TOKEN in self.payload, "Payload doesn't look like it belongs to PhyML"

        self.jmodel_modelname = self.payload.split(MODELNAME_TOKEN)[1].split()[0]
        self.jmodel_runid = sns_message['Subject']
        filedata = filepath.split('://')

        return {'bucket': filedata[0], 'key': filedata[1]}


class S3Download:

    def __init__(self, finfo, file_subject):
        self.__file_info = finfo
        self.__generate_temp_paths(file_subject)

        if os.path.exists(self.local_file):
            logging.warn("File already exists {}".format(self.local_file))
        else:
            logging.info("Downloading to: {}".format(self.local_file))
            self.__download()

    def __generate_temp_paths(self, file_subject):
        self.tmp_folder = os.path.join(
            TEMP_FOLDER_PREFIX, 
            correlation_id
        )
        self.local_file = os.path.join(
            TEMP_FOLDER_PREFIX, 
            correlation_id, 
            file_subject
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
        self.files = {x: self.__FixPhymlTraceFilenames(x, sns_result.jmodel_runid) for x in files}

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

    def __FixPhymlTraceFilenames(self, filename, file_subject):

        remove_redundant = filename.replace(file_subject + "_phyml_", "")
        remove_extension = remove_redundant[:-4]

        # make sure to keep Model identifier
        assert self.__jmodel_modelname in remove_extension, "Fixed filename lost Model name"

        reverse = reversed(remove_extension.split("_"))
        result = ("_".join(reverse)) + ".txt"

        return result


class Batch:
    
    def __init__(self, jobdef, jobq, payload):
        response = batch_client.submit_job(
            jobName       = payload['sourcerequestid'],
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
    
    
    @staticmethod
    def TriggerCompute(job_queue, job_compute_env, runnableToCpuRatio=(3/4)):
        
        response = batch_client.describe_compute_environments(computeEnvironments=[job_compute_env])
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.Describe_ComputeEnvironments"

        envdata = response['computeEnvironments'][0]
        if envdata['status'] == 'UPDATING': 
            return
        
        assert envdata['state'] == 'ENABLED' and envdata['status'] == 'VALID', "ComputeEnvironment in invalid state"

        # query runnable
        response = batch_client.list_jobs(jobQueue=job_queue,jobStatus='RUNNABLE')
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.List_Jobs"
        runnable = len(response['jobSummaryList'])
        # query submitted
        response = batch_client.list_jobs(jobQueue=job_queue,jobStatus='SUBMITTED')
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.List_Jobs"
        submitted = len(response['jobSummaryList'])
        
        desired = envdata['computeResources']['desiredvCpus']
        maximum = envdata['computeResources']['maxvCpus']

        # cluster size 'heuristic'
        gross_new_cpu = (runnable + submitted) * runnableToCpuRatio
        net_new_cpu = math.ceil(gross_new_cpu / 2.0) * 2    # rounded to nearest even number
        new_cpus = min(maximum, net_new_cpu)
        algorithm_state = { 
            'RUNNABLE':  runnable,
            'SUBMITTED': submitted,
            'DESIRED':   desired,
            'MAX':       maximum,
            'STATE':     envdata['state'],
            'STATUS':    envdata['status']
        }

        if (desired < new_cpus):
            logging.warn("Triggering update to '{}' CPUs in ComputeEnvironment ({})".format(new_cpus, json.dumps(algorithm_state)))

            response = batch_client.update_compute_environment(
                computeEnvironment=job_compute_env,
                computeResources={
                    'desiredvCpus': new_cpus
                }
            )
            assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.Update_ComputeEnvironment"
    
    
    @staticmethod
    def shortcircuit(job_queue):

        # queue info
        response = batch_client.describe_job_queues(jobQueues=[job_queue])
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.Describe_Queues"
        queuedata = response['jobQueues'][0]
        assert queuedata['state'] == 'ENABLED' and queuedata['status'] == 'VALID', "Queue in invalid state"
        environment = queuedata['computeEnvironmentOrder'][0]['computeEnvironment']

        # compute info
        response = batch_client.describe_compute_environments(computeEnvironments=[environment])
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.Describe_ComputEnvironments"
        envdata = response['computeEnvironments'][0]
        assert envdata['state'] == 'ENABLED' and envdata['status'] == 'VALID', "ComputeEnvironment in invalid state"
        capacity = envdata['computeResources']['maxvCpus']
        is_running = envdata['computeResources']['desiredvCpus']


        # queue runnable
        response = batch_client.list_jobs(jobQueue=job_queue,jobStatus='RUNNABLE')
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.List_Jobs"
        runnable = len(response['jobSummaryList'])

        # queue running
        response = batch_client.list_jobs(jobQueue=job_queue,jobStatus='RUNNING')
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.List_Jobs"
        running = len(response['jobSummaryList'])


        # should short circuit?
        return is_running and capacity > (runnable + running)


class DynamoDB:
    
    def __init__(self, table_name, model_name):
        response = dynamo_client.delete_item(
            TableName=table_name,
            Key={
                'Model': {
                    'S': model_name
                }
            }
        )

        assert response['ResponseMetadata']['HTTPStatusCode'] == 200, "Bad response from Batch.Submit_Job"
