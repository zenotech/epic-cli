_URL_ROOT = '/api/v1/'
AUTH = _URL_ROOT + 'auth/'
PROJECTS_LIST = _URL_ROOT + 'billing/projectcode/list/'
TEAMS_LIST = _URL_ROOT + 'teams/list/'
DATA_LIST = _URL_ROOT + 'data/aws/list/'
DATA_LOCATION = _URL_ROOT + 'data/aws/get/'
BATCH_QUEUES = _URL_ROOT + 'batch/queues/'
BATCH_APPLICATIONS = _URL_ROOT + 'batch/app/list'
BATCH_JOB_LIST = _URL_ROOT + 'batch/job/list/'
AWS_GET = _URL_ROOT + 'accounts/aws/get/'
AWS_CREATE = _URL_ROOT + 'accounts/aws/create/'
AWS_DATA_GET = _URL_ROOT + 'data/aws/get/'
BATCH_JOB_CANCEL = _URL_ROOT + 'batch/job/cancel/'
CLUST_LIST = _URL_ROOT + 'batch/app/'
BATCH_JOB_DELETE = _URL_ROOT + 'batch/job/delete/'


def application_version(app_id):
    return _URL_ROOT + 'batch/app/' + str(app_id) + '/versions/'


def queue_details(queue_id):
    return _URL_ROOT + 'batch/queues/' + str(queue_id) + '/'


def job_details(job_id):
    return _URL_ROOT + 'batch/job/' + str(job_id) + '/'
