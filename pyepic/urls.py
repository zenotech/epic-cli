_URL_ROOT = '/api/v1/'
AUTH = _URL_ROOT + 'auth/'
PROJECTS_LIST = _URL_ROOT + 'billing/projectcode/list/'
TEAMS_LIST = _URL_ROOT + 'teams/list/'
DATA_LIST = _URL_ROOT + 'data/aws/list/'
DATA_LOCATION = _URL_ROOT + 'data/aws/get/'
BATCH_QUEUES = _URL_ROOT + 'batch/queues/'
BATCH_APPLICATIONS = _URL_ROOT + 'batch/app/list'
BATCH_JOB_CREATE = _URL_ROOT + 'batch/job/create/'
BATCH_JOB_COST = _URL_ROOT + 'batch/job/quote/'
BATCH_JOB_STATUS = _URL_ROOT + 'batch/job/status/'
BATCH_JOB_LIST = _URL_ROOT + 'batch/job/list/'
ACCOUNT_CREDENTIALS = _URL_ROOT + 'accounts/aws/get/'

def application_version(app_id):
	return _URL_ROOT + 'batch/app/' + str(app_id) + '/versions/'


