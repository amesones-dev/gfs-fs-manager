import os
import logging
from google.cloud import firestore
from google.cloud.firestore_v1.base_document import DocumentSnapshot
from google.cloud.firestore_v1.base_query import FieldFilter


# Google Firestore manager class
class GFSManager:
    def __init__(self):
        self.__path_prefix = None
        self.__fs_client = None

    @property
    def path_prefix(self):
        return self.__path_prefix

    @property
    def client(self):
        # Firestore client
        return self.__fs_client

    def init_app(self, app):
        # Creates a firestore client per application instance
        # Using credentials from service account file
        # Service Account role: access to Firestore for read/write

        if self.validate_app(app):
            sa_creds_json_file = app.config['FSM_SA_KEY_JSON_FILE']
            if sa_creds_json_file == "":
                # Default Google Cloud application credentials
                try:
                    self.__fs_client = firestore.Client()
                except Exception as e:
                    logging.log(level=logging.ERROR,
                                msg="Exception {}:{} Method: {}".format(e.__class__, e, self.init_app.__name__))
                    pass
            else:
                # Credential from file
                try:
                    self.__fs_client = firestore.Client.from_service_account_json(sa_creds_json_file)
                except Exception as e:
                    logging.log(level=logging.ERROR,
                                msg="Exception {}:{} Method: {}".format(e.__class__, e, self.init_app.__name__))
                    pass

            if self.__fs_client is not None:
                # Dictionary with app details, versioning, owner, etc.
                app_data = app.config['FSM_APP_INFO_DATA']

                # Firestore operation
                try:
                    # Create a FS document reference to store app data
                    app_doc = self.__fs_client.collection(app.config['FSM_APP_ROOT']).document(
                        app.config['FSM_APP_OBJECTS_PATH']).get()
                    if not app_doc.exists:
                        # Create Firestore document in collection apps at FSM_APP_OBJECTS_PATH from app config class
                        self.__fs_client.collection(app.config['FSM_APP_ROOT']).document(
                            app.config['FSM_APP_OBJECTS_PATH']).set(app_data)
                    self.__path_prefix = app.config['FSM_APP_ROOT'] + '/' + app.config['FSM_APP_OBJECTS_PATH']
                except Exception as e:
                    logging.log(level=logging.ERROR,
                                msg="Exception {}:{} Method: {}".format(e.__class__, e, self.init_app.__name__))
                    pass

    def initialized(self) -> bool:
        return self.client is not None \
               and isinstance(self.client, firestore.Client) \
               and self.__path_prefix is not None

    def close_connection(self):
        if self.initialized():
            self.client.close()

    def validate_properties(self, doc_properties):
        validation = False
        if isinstance(doc_properties, dict):
            validation = True
        return validation

    # Creates a new Firestore Document with properties as doc_properties at fs_collection_path
    # If no fs_collection_path provided, FS Document is created under a FS Collection called as the app_object class
    # Under the current GFSManager Firestore realm (self.path_prefix)

    def fs_doc_store(self, app_object, doc_properties, fs_collection_path=None, *args, **kwargs):
        fs_id = None
        fs_stored_time = None
        fs_path = None
        result = False

        # Default collection path
        # Map object class to Firestore Collection by default
        # fs_collection_path takes precedence if indicated
        if fs_collection_path is None:
            fs_collection_name = app_object.__class__.__name__
            fs_collection_path = self.path_prefix + '/' + fs_collection_name
        if self.validate_properties(doc_properties=doc_properties):
            # Creates a Firestore Document at parent collection fs_collection_path
            # If collection path does not exist, Firestore creates it automatically
            try:
                fs_stored_time, fs_stored_object = self.client.collection(fs_collection_path).add(
                    document_data=doc_properties)
                # TODO: Validate stored object returned (class and contains id and path property)
                fs_id = fs_stored_object.id
                fs_path = fs_stored_object.path
                result = True
            except Exception as e:
                logging.log(level=logging.ERROR,
                            msg="Exception {}:{} Method: {}".format(e.__class__, e, self.init_app.__name__))
                result = False
        return fs_stored_time, fs_id, fs_path, result

    # Given an existing id, replaces current object properties with doc_properties
    def fs_doc_update(self, fs_id, doc_properties, fs_collection_path=None, *args, **kwargs):
        fs_stored_time = None
        fs_path = None
        result = False
        if self.validate_properties(doc_properties=doc_properties):
            try:
                fs_doc_ref = self.client.collection(fs_collection_path).document(document_id=fs_id)
                if fs_doc_ref.get().exists:
                    fs_write_result = fs_doc_ref.set(document_data=doc_properties)
                    result = isinstance(fs_write_result, firestore.types.write.WriteResult)
                    if result:
                        # Read actual values from Firestore
                        fs_stored_time = fs_write_result.update_time
                        fs_path = fs_doc_ref.path
                        # Updated existing FS document
            except Exception as e:
                logging.log(level=logging.ERROR,
                            msg="Exception {}:{} Method: {}".format(e.__class__, e, self.init_app.__name__))
                result = False
        return fs_stored_time, fs_id, fs_path, result

    def fs_doc_properties(self, fs_id, fs_collection_path=None, *args, **kwargs) -> dict:
        fs_doc_properties = None
        fs_doc_ref = self.client.collection(fs_collection_path).document(document_id=fs_id)
        if isinstance(fs_doc_ref, firestore.DocumentReference):
            if fs_doc_ref.get().exists:
                fs_doc_snapshot = fs_doc_ref.get()
        fs_doc_properties = fs_doc_snapshot.to_dict()
        return fs_doc_properties

    def fs_doc_exist(self, fs_doc_path) -> bool:
        doc_ref = self.client.document(fs_doc_path)
        return doc_ref.get().exists

    def fs_doc_delete(self, fs_id, fs_path):
        result = False
        fs_deleted_time = None
        if fs_id is not None:
            doc = self.client.document(fs_path)
            if isinstance(doc, firestore.DocumentReference):
                if doc.id == fs_id:
                    if doc.get().exists:
                        # The Firestore Document delete() operations returns a DatetimeWithNanoseconds in python
                        fs_deleted_time = doc.delete()
                        result = not doc.get().exists
        return fs_deleted_time, fs_id, fs_path, result

    def fs_query_by_id(self, lookup_id, app_object=None, parent_doc_path=None, lookup_collection=None) \
            -> DocumentSnapshot:
        result = None
        if lookup_collection is None:
            if app_object is not None:
                lookup_collection = app_object.__class__.__name__

        # Lookup collection provided or populated from app_object
        if lookup_collection is not None:
            # Include paren_doc_path if present
            if parent_doc_path is not None:
                col_path = parent_doc_path + '/' + lookup_collection
            else:
                # Default collection path
                col_path = self.__path_prefix + '/' + lookup_collection

            # Firestore Operation
            try:
                fs_doc_ref = self.client.collection(col_path).document(document_id=lookup_id)
                fs_doc = fs_doc_ref.get()
                if fs_doc.exists:
                    result = fs_doc
            except Exception as e:
                logging.log(level=logging.ERROR, msg="Exception {}:{} Method: {}".format(e.__class__, e,
                                                                                         self.fs_query_by_id.__name__))
                result = None
        return result

    # Return all Firestore documents representing objects of the same class/collection
    # stored under the same parent document

    def fs_query_by_collection(self, app_object=None, parent_doc_path=None, lookup_collection=None) -> list:
        # By design Firestore collection is mapped to derived class name dynamically
        # Returns a list of objects Firestore document snapshot (contains id, reference to Firestore and path)
        # If lookup_collection provided, lookup_collection takes precedence
        results = None
        if lookup_collection is None:
            if app_object is not None:
                lookup_collection = app_object.__class__.__name__

        # Lookup collection provided or populated from app_object
        if lookup_collection is not None:
            # Include paren_doc_path if present
            if parent_doc_path is not None:
                col_path = parent_doc_path + '/' + lookup_collection
            else:
                # Default collection path
                col_path = self.__path_prefix + '/' + lookup_collection

            # Firestore Operation
            try:
                col_ref = self.__fs_client.collection(col_path)
                docs = col_ref.stream()
                # docs is a class generator
                # Add every doc to results list
                # to cast every object to Firestore DocumentSnapshot object
                results = []
                for doc in docs:
                    results.append(doc)
            except Exception as e:
                logging.log(level=logging.ERROR, msg="Exception {}:{} Method: {}".format(e.__class__, e,
                                                                                         self.fs_query_by_collection.__name__))
                results = None

        return results

    def fs_query_by_properties(self, lookup_properties, app_object=None, parent_doc_path=None, lookup_collection=None) \
            -> list:
        # By design Firestore collection is mapped to derived class name dynamically
        # Returns a list of objects Firestore document snapshot (contains id, reference to Firestore and path)
        # If lookup_collection provided, lookup_collection takes precedence
        results = None
        if lookup_collection is None:
            if app_object is not None:
                lookup_collection = app_object.__class__.__name__

        # Lookup collection provided or populated from app_object
        if lookup_collection is not None:
            # Include paren_doc_path if present
            if parent_doc_path is not None:
                col_path = parent_doc_path + '/' + lookup_collection
            else:
                # Default collection path
                col_path = self.__path_prefix + '/' + lookup_collection

            # Firestore Operation
            try:
                col_ref = self.__fs_client.collection(col_path)
                for lookup_property in lookup_properties:
                    # Firestore warning produced if no FieldFilter class used
                    # query = query.where(field_path=lookup_property, op_string='==',
                    # value=lookup_properties.get(lookup_property))
                    query = col_ref.where(filter=FieldFilter(field_path=lookup_property, op_string='==',
                                                             value=lookup_properties.get(lookup_property)))
                docs = query.stream()
                # Docs return a class generator
                # Add every doc to results list
                # to cast every object to Firestore DocumentSnapshot object

                # docs is a class generator
                # Add every doc to results list
                # to cast every object to Firestore DocumentSnapshot object
                results = []
                for doc in docs:
                    results.append(doc)
            except Exception as e:
                logging.log(level=logging.ERROR, msg="Exception {}:{} Method: {}"
                            .format(e.__class__, e, self.fs_query_by_collection.__name__))
                results = None

        return results

    def fs_delete_collection(self, app_object=None, parent_doc_path=None, lookup_collection=None):
        # Deletes all the current objects in a collection
        # By design Firestore collection maps to derived class name dynamically
        result = False
        if lookup_collection is None:
            if app_object is not None:
                lookup_collection = app_object.__class__.__name__

        # Lookup collection provided or populated from app_object
        if lookup_collection is not None:
            # Include paren_doc_path if present
            if parent_doc_path is not None:
                col_path = parent_doc_path + '/' + lookup_collection
            else:
                # Default collection path
                col_path = self.__path_prefix + '/' + lookup_collection
                # Firestore Operation
            try:

                col_ref = self.client.collection(col_path)
                fs_docs = col_ref.stream()

                # Collection deletion fails is at least one document is not deleted
                one_non_deleted = False
                for fs_doc in fs_docs:
                    fs_doc.reference.delete()
                    one_non_deleted = one_non_deleted or fs_doc.reference.get().exists
                result = not one_non_deleted
            except Exception as e:
                logging.log(level=logging.ERROR, msg="Exception {}:{} Method: {}"
                            .format(e.__class__, e, self.fs_delete_collection.__name__))
                result = False
        return result

    # Validates whether an app can be integrated with gbq_manager
    @staticmethod
    def validate_app(app) -> bool:
        # App: any object that has a 'config' property which is a dictionary
        # Example: could be a Flask app, a FastAPI app, etc.
        # For the app to use the GFSManager, the dictionary must contain the following key values.

        # For the app to use the FirestoreManager, the dictionary must contain the following key values.
        # app.config['FSM_APP_ROOT']:  Name of Firestore collection to hold App documents. It allows for multi-tenancy.
        # app.config['FSM_APP_OBJECTS_PATH']: Path relative to Apps collection where to store a specific App objects.
        # app.config['FSM_APP_INFO_DATA']:  Dictionary with this specific App details, versioning, owner, etc.

        # app.config['FSM_SA_KEY_JSON_FILE']: path to Google Cloud Project Service Account credentials file.
        # Option 1. Valid path to existent  Google Cloud service account key json file
        # FROM OS or known filesystem path
        # FSM_SA_KEY_JSON_FILE = os.environ.get('FSM_SA_KEY_JSON_FILE') or '/etc/secrets/sa_key_fs.json'

        # Option 2. Empty string to use Google Cloud Application credentials environment
        # Default Google Cloud Application credentials
        # FSM_SA_KEY_JSON_FILE = ''

        validation = False
        required = ['FSM_SA_KEY_JSON_FILE', 'FSM_APP_ROOT', 'FSM_APP_OBJECTS_PATH', 'FSM_APP_INFO_DATA']
        if 'config' in app.__dict__:
            if isinstance(app.config, dict):
                # Check mandatory config keys exist
                if set(required).issubset(app.config.keys()):
                    # Check FSM_APP_INFO_DATA is a dictionary
                    if isinstance(app.config.get('FSM_APP_INFO_DATA'), dict):
                        validation = app.config['FSM_SA_KEY_JSON_FILE'] == "" or \
                                     (app.config['FSM_SA_KEY_JSON_FILE'] != ""
                                      and os.path.isfile(app.config['FSM_SA_KEY_JSON_FILE']))
        return validation
