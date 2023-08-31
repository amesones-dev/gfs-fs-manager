import os


# App: any object that has a 'config' property which is a dictionary
# Example: a Flask app
# For the app to use the FirestoreManager, the app configuration  must contain the following key values.
# app.config['FSM_SA_KEY_JSON_FILE']: path to Google Cloud Project Service Account credentials file.
# Use an empty string to use default Google Cloud application credentials
# app.config['FSM_APP_ROOT']:  Name of Firestore collection to hold App documents. It allows for multi-tenancy.
# app.config['FSM_APP_OBJECTS_PATH']: Path relative to Apps collection where to store a specific App objects.
# app.config['FSM_APP_INFO_DATA']:  Dictionary with this specific App details, versioning, owner, etc.

class TestConfig(object):
    settings = ['FSM_VIEW_APP_NAME', 'FSM_APP_INFO_DATA', 'FSM_APP_ROOT', 'FSM_SA_KEY_JSON_FILE', 'FSM_APP_OBJECTS_PATH']
    # Application FS details
    FSM_VIEW_APP_NAME = os.environ.get('FSM_VIEW_APP_NAME') or 'gfs-fs-manager'
    FSM_APP_INFO_DATA = {'description': 'Firestore Manager Base', 'version': '1.0', 'stage': 'alpha', 'env': 'test'}
    # Firestore applications root
    # Allows to store several app configurations under one FS database
    FSM_APP_ROOT = 'gfs_tests'

    # Google Cloud service account key json file
    # FROM OS or known filesystem path
    # FSM_SA_KEY_JSON_FILE = os.environ.get('FSM_SA_KEY_JSON_FILE') or '/etc/secrets/sa_key_fs.json'
    # Force using ENV variable for tests
    FSM_SA_KEY_JSON_FILE = os.environ.get('TEST_FSM_SA_KEY_JSON_FILE')
    # Default Google Cloud Application credentials
    # FSM_SA_KEY_JSON_FILE = ''
    FSM_APP_OBJECTS_PATH = os.environ.get('FSM_APP_OBJECTS_PATH') or "gfs_manager_dev"

    def to_dict(self):
        r = {}
        for k in self.settings:
            r[k] = self.__getattribute__(k)
        return r
