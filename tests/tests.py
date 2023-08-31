import random
import unittest
import warnings

# App specific imports
from gfs_manager import GFSManager
from google.cloud import firestore
# FSMConfig imports
from config import TestConfig


class MockFSOApp:
    def __init__(self, config_class=TestConfig):
        self.config = config_class().to_dict()


class MockFSOAppObject:
    def __init__(self):
        pass


class FireStoreManagerModelCase(unittest.TestCase):
    def setUp(self):
        test_app = MockFSOApp(config_class=TestConfig)

        # Link to Firestore adapter
        fs = GFSManager()
        fs.init_app(test_app)

        self.app = test_app
        self.fs = fs
        # Test logging configuration
        warnings.filterwarnings(action="ignore", category=ResourceWarning)

    def tearDown(self):
        self.fs.close_connection()

    def test_0_validate_app(self):
        # app.config['FSM_SA_KEY_JSON_FILE']: path to Google Cloud Project Service Account credentials file.
        # app.config['FSM_APP_ROOT']:  Name of Firestore collection to hold App documents. It allows for multi-tenancy.
        # app.config['FSM_APP_OBJECTS_PATH']: Path relative to Apps collection where to store a specific App objects.
        # app.config['FSM_APP_INFO_DATA']:  Dictionary with this specific App details, versioning, owner, etc.

        # Save original config
        sa_creds = self.app.config.get('FSM_SA_KEY_JSON_FILE')

        # Validate app with original configuration
        self.assertTrue(self.fs.validate_app(self.app))

        # Modify config to trigger validation error
        self.app.config.update({'FSM_SA_KEY_JSON_FILE': '/non_existent_dir/non_existent_file/'})
        self.assertFalse(self.fs.validate_app(self.app))

        # Restore original config
        self.app.config.update({'FSM_SA_KEY_JSON_FILE': sa_creds})
        self.assertTrue(self.fs.validate_app(self.app))

        app_data = self.app.config.get('FSM_APP_INFO_DATA')

        # Modify config to trigger validation error
        non_valid_app_data = "This is not a dictionary, but a string"
        self.app.config.update({'FSM_APP_INFO_DATA': non_valid_app_data})
        self.assertFalse(self.fs.validate_app(self.app))

        # Restore original config
        self.app.config.update({'FSM_APP_INFO_DATA': app_data})
        self.assertTrue(self.fs.validate_app(self.app))

    def test_1_init_app(self):
        self.assertTrue(self.fs.validate_app(self.app))
        self.fs.init_app(self.app)
        self.assertTrue(self.fs.initialized())

    def test_2_save_object(self):
        self.assertTrue(self.fs.initialized())
        app_object = MockFSOAppObject()
        app_object_properties = {'x': 100, 'title': "Nunc es bibendum"}
        fs_stored_time, fs_id, fs_path, result = self.fs.fs_doc_store(app_object=app_object,
                                                                      doc_properties=app_object_properties)
        self.assertIsNotNone(fs_stored_time)
        self.assertIsNotNone(fs_id)
        self.assertIsNotNone(fs_path)
        self.assertTrue(result)

        # Delete object
        self.fs.fs_doc_delete(fs_id=fs_id, fs_path=fs_path)

    def test_3_update_object(self):
        self.assertTrue(self.fs.initialized())
        app_object = MockFSOAppObject()
        app_object_poperties = {'x': 100, 'title': "Nunc es bibendum"}
        fs_stored_time, fs_id, fs_path, store_result = self.fs.fs_doc_store(app_object=app_object,
                                                                            doc_properties=app_object_poperties)
        self.assertIsNotNone(fs_stored_time)
        self.assertIsNotNone(fs_id)
        self.assertIsNotNone(fs_path)
        self.assertTrue(store_result)

        # Updates new object
        update_result = False
        fs_collection_name = app_object.__class__.__name__
        fs_collection_path = self.fs.path_prefix + '/' + fs_collection_name
        new_properties = {'y': 300}
        update = self.fs.fs_doc_update(fs_id=fs_id, fs_collection_path=fs_collection_path,
                                       doc_properties=new_properties)
        update_result = update[3]
        self.assertTrue(update_result)
        fs_properties = self.fs.fs_doc_properties(fs_id=fs_id, fs_collection_path=fs_collection_path)
        self.assertEqual(new_properties, fs_properties)

    def test_4_delete_object(self):
        self.assertTrue(self.fs.initialized())
        app_object = MockFSOAppObject()
        app_object_properties = {'x': 100, 'title': "Nunc es bibendum"}
        fs_stored_time, fs_id, fs_path, store_result = \
            self.fs.fs_doc_store(app_object=app_object, doc_properties=app_object_properties)
        self.assertIsNotNone(fs_stored_time)
        self.assertIsNotNone(fs_id)
        self.assertIsNotNone(fs_path)
        self.assertTrue(store_result)

        # Deletes new object
        delete_result = False
        fs_deleted_time, fs_deleted_id, fs_deleted_path, delete_result = self.fs.fs_doc_delete(fs_id=fs_id, fs_path=fs_path)
        self.assertTrue(delete_result)
        self.assertIsNotNone(fs_deleted_time)
        self.assertEqual(fs_id, fs_deleted_id)
        self.assertEqual(fs_path, fs_deleted_path)

    def test_5_query_by_id(self):
        self.assertTrue(self.fs.initialized())
        app_object = MockFSOAppObject()
        app_object_properties = {'x': 100, 'title': "Nunc es bibendum"}
        fs_stored_time, fs_id, fs_path, result = self.fs.fs_doc_store(app_object=app_object,
                                                                      doc_properties=app_object_properties)
        self.assertIsNotNone(fs_stored_time)
        self.assertIsNotNone(fs_id)
        self.assertIsNotNone(fs_path)
        self.assertTrue(result)

        # def fs_query_by_id(self, lookup_id, app_object=None, parent_doc_path=None, lookup_collection=None) \
        recovered_fs_doc = self.fs.fs_query_by_id(lookup_id=fs_id, app_object=app_object)
        self.assertIsInstance(recovered_fs_doc, firestore.DocumentSnapshot)
        self.assertEqual(fs_id, recovered_fs_doc.id)
        self.assertEqual(fs_id, recovered_fs_doc.reference.id)
        self.assertEqual(fs_path, recovered_fs_doc.reference.path)
        self.assertEqual(app_object_properties, recovered_fs_doc.to_dict())


        # Delete object
        self.fs.fs_doc_delete(fs_id=fs_id, fs_path=fs_path)

    def test_6_lookup_by_collection(self):
        fs = self.fs
        for a in range(1, 5):
            app_object = MockFSOAppObject()
            app_object_properties = {'x': random.randint(0, 100), 'y': random.randint(0, 100)}
            self.fs.fs_doc_store(app_object=app_object, doc_properties=app_object_properties)

        fs_docs_1 = fs.fs_query_by_collection(app_object=MockFSOAppObject())

        lookup_collection = app_object.__class__.__name__
        fs_docs_2 = fs.fs_query_by_collection(lookup_collection=lookup_collection)

        # This is true if fs returns the objects in the same order when querying Firestore
        self.assertEqual(fs_docs_1, fs_docs_2)

        # If order is not guaranteed, this test is more accurate
        self.assertEqual(fs_docs_1.__len__(), fs_docs_2.__len__())
        docs_ids_1 = set([doc.id for doc in fs_docs_1])
        docs_ids_2 = set([doc.id for doc in fs_docs_2])
        self.assertEqual(docs_ids_1, docs_ids_2)

    def test_7_lookup_by_properties(self):
        fs = self.fs
        for a in range(1, 5):
            app_object = MockFSOAppObject()
            if a > 2:
                app_object_properties = {'x': 1, 'y': 3}
            else:
                app_object_properties = {'x': 2, 'y': 4}
            self.fs.fs_doc_store(app_object=app_object, doc_properties=app_object_properties)

        fs_docs_1 = fs.fs_query_by_properties(lookup_properties={'x': 1}, app_object=MockFSOAppObject())

        # Check every Firestore Document returned has amongst its data 'x' as key, and the value for said key is 1
        data_check_1 = [doc.to_dict().get('x') == 1 for doc in fs_docs_1]
        self.assertTrue(data_check_1.count(True), data_check_1.__len__())

        lookup_collection = app_object.__class__.__name__
        fs_docs_2 = fs.fs_query_by_properties(lookup_properties={'x': 1}, lookup_collection=lookup_collection)

        # This is true if fs returns the objects in the same order when querying Firestore
        self.assertEqual(fs_docs_1, fs_docs_2)

        # If order is not guaranteed, this test is more accurate
        self.assertEqual(fs_docs_1.__len__(), fs_docs_2.__len__())
        docs_ids_1 = set([doc.id for doc in fs_docs_1])
        docs_ids_2 = set([doc.id for doc in fs_docs_2])
        self.assertEqual(docs_ids_1, docs_ids_2)

        fs_docs_3 = fs.fs_query_by_properties(lookup_properties={'x': 2}, app_object=MockFSOAppObject())
        fs_docs_4 = fs.fs_query_by_properties(lookup_properties={'x': 2}, lookup_collection=lookup_collection)

        # This is true if fs returns the objects in the same order when querying Firestore
        self.assertEqual(fs_docs_3, fs_docs_4)

        # If order is not guaranteed, this test is more accurate
        self.assertEqual(fs_docs_3.__len__(), fs_docs_4.__len__())
        docs_ids_3 = set([doc.id for doc in fs_docs_3])
        docs_ids_4 = set([doc.id for doc in fs_docs_4])
        self.assertEqual(docs_ids_3, docs_ids_4)

        fs_docs_5 = fs.fs_query_by_properties(lookup_properties={'x': 1, 'y': 3}, app_object=MockFSOAppObject())
        fs_docs_6 = fs.fs_query_by_properties(lookup_properties={'x': 1, 'y': 3}, lookup_collection=lookup_collection)

        # Check every Firestore Document returned has amongst its data 'x' as key, and the value for said key is 1
        # And 'y' as key, and teh value for said key is 3
        data_check_5 = [doc.to_dict().get('x') == 1 and  doc.to_dict().get('y') == 3 for doc in fs_docs_1]
        self.assertTrue(data_check_5.count(True), data_check_5.__len__())

        # This is true if fs returns the objects in the same order when querying Firestore
        self.assertEqual(fs_docs_5, fs_docs_6)

        # If order is not guaranteed, this test is more accurate
        self.assertEqual(fs_docs_5.__len__(), fs_docs_6.__len__())
        docs_ids_5 = set([doc.id for doc in fs_docs_5])
        docs_ids_6 = set([doc.id for doc in fs_docs_6])
        self.assertEqual(docs_ids_5, docs_ids_6)

    def test_8_delete_collection(self):

        self.assertTrue(self.fs.initialized())
        for a in range(1, 5):
            app_object = MockFSOAppObject()
            app_object_properties = {'x': random.randint(0, 100), 'y': random.randint(0, 100)}
            self.fs.fs_doc_store(app_object=app_object, doc_properties=app_object_properties)
        before_fs_docs = self.fs.fs_query_by_collection(lookup_collection=app_object.__class__.__name__)
        collection_deleted = self.fs.fs_delete_collection(lookup_collection=app_object.__class__.__name__)
        after_fs_docs = self.fs.fs_query_by_collection(lookup_collection=app_object.__class__.__name__)

        self.assertTrue(collection_deleted)
        before_fs_docs_ids = set([doc.id for doc in before_fs_docs])
        after_fs_docs_ids = set([doc.id for doc in after_fs_docs])
        # Check all the original docs have been deleted
        # If there are ids from original docs
        # Either collection deletion has failed
        # There might be new objects in the same collection created by some other process
        # But that does not imply an error deleting objects in collection
        self.assertNotIn(after_fs_docs_ids, before_fs_docs_ids)


if __name__ == '__main__':
    unittest.main(verbosity=2)
