# gfs-fs-manager
#### "A simple Google Firestore connection manager"

## Connecting your application to Google Cloud Firestore
A basic connection manager to leverage [Firestore API Client Libraries](https://cloud.google.com/python/docs/reference/firestore/latest)
to use [Firestore](https://cloud.google.com/firestore/)  database for python applications.

## Google Cloud requirements  
* Existing project with a Firestore database
* Firestore API enabled: firestore.googleapis.com  

**Reference**
* [Create a Firestore database](https://cloud.google.com/firestore/docs/create-database-server-client-library)
  


## GFSManager class
1. Creates a  Firestore API client from a service account key file  
*Note: required IAM roles for service account: DataStore User*

2. Isolates Firestore connections management

Reference:  
* [Firestore client library](https://cloud.google.com/firestore/docs/reference/libraries#google_cloud_client_libraries)
* [Firestore IAM roles](https://cloud.google.com/firestore/docs/security/iam) 


**Class use example to manage Firestore connections for an app**  
*Link GFSManager to app*

```python
from gfs_manager import GFSManager
# Link app to Firestore manager
fsm = GFSManager()
fsm.init_app(_app)
```

## Configuring your application
**Application**
* Any object that has a 'config' property which is a dictionary
* Custom keys and values can be added to 'config'
* Example: could be a Flask app, a FastAPI app, etc.* 


**Objects hierarchical storage**  

GFSManager stores all objects created by an application  under a specific path, unique for every application, allowing 
using one Firestore database for several applications. 

* GFSManager creates or use an existing root Firestore Collection (FSM_APP_ROOT) to organize stored objects per app.
* GFSManager creates a Firestore Document, member of the FSM_APP_ROOT Collection,  representing the current app. 

The Firestore document includes:
1. User defined properties representing the App. A dictionary called FSM_APP_INFO_DATA is used as template for the 
  Firestore document property.
2. Child Collections of objects managed by the app. 
 
When GFSManager stores an object for the current app:
   1. Creates a new Collection or use an existing Collection with the same name as the object Class
   2. Stores the object as a Document within the Collection. 
   
**App configuration keys used by GFSManager class**  

```console
   # Google Cloud service account key json file
   # Determines service account and hence Firestore permissions
    FSM_SA_KEY_JSON_FILE = os.environ.get('FSM_SA_KEY_JSON_FILE') or '/etc/secrets/sa_key_fs.json'
    
    # If defined and empty, application uses Application Default Credentials
    FSM_SA_KEY_JSON_FILE = ''
    
    # Application Firestore database structure settings
    
    # Firestore applications root
    # Name of Firestore collection to hold a hierarchy of apps related objects, stored as Firestore Documents.
    FSM_APP_ROOT = 'tier1-apps-dev'
    
    # Firestore specific app database path
    # Path relative to apps root collection where to store a specific App objects.
    FSM_OBJECTS_PATH = "fancy-app"
    
    # Specific app info
    # Dictionary with a specific app details: versioning, owner, etc.
    FSM_APP_INFO_DATA = {'description': 'Fancy flask app objects database ', 'version': '1.0', 'stage': 'alpha', 'env': 'dev'}
    
```

**Reference**  
* [Authenticating as a service account](https://cloud.google.com/docs/authentication/production#auth-cloud-explicit-python)
* [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
* [Service Account(SA) key](https://cloud.google.com/iam/docs/keys-create-delete)


## Multi tenancy in a single Google Cloud project
**Firestore constraints**
* At the moment, Firestore supports only one database per project.
* Firestore supports Collections within documents
* Collections within Collections are not supported

GFSManager allows storing application objects of different applications if so wished in the same Firetore database, 
which is specially useful during the design process of a solution, or when sharing expensive resources for dev 
environments.

**Several Firestore root Collections of apps per project**  

 One way to achieve multi tenancy within a single project is by means of one or more root collections of Firestore 
 Documents representing apps. When using GFSManager, the root collection that the managed app and their objects belong 
 to is configured with the FSM_APP_ROOT setting.

**One Firestore document per app**  
Every app document contains **properties** defined in FSM_APP_INFO_DATA config key that identify the specific 
application. When using GFSManager, the app Firestore Document is configured with the FSM_APP_OBJECTS_PATH.
```console
{'description': 'Fancy flask app objects database ', 'version': '1.0', 'stage': 'alpha', 'env': 'dev'}
```
**Every app holds collections of app objects**  
Every app document will hold child Collections of application specific objects, every one 
of them stored as Firestore Documents with their unique id, path under the owner app withing a Collection called 
according to their origin class (Users, Posts, Messages, etc.) and their own set of **properties**.
 
* Within a single project Firestore database, one or more root Collections can be defined, with several 
*child Documents* representing apps:  
   * /apps-root1/app1
   * /apps-root1/app2
   * /apps-root2/app3

* Every Document (app1_name, app2_name, etc.). can act as a root path for *Collections* storing objects for 
 that specific app instance.  
  * /apps-root1/app1/Users
  * /apps-root1/app1/Posts
  * /apps-root1/app1/Images


    
## Example
Given the following Firestore *paths* for existing Firestore Documents in the Google Cloud project Firestore database,

* /tier1-apps-dev/quickstart/**User**/w6lm7VRihyOGUb2VH1WS
* /tier1-apps-dev/quickstart/**WebSession**/zurcUNUB45cNOVKYREke
* /tier1-apps-dev/quickstart/**User**/w6lm7VRihyOGUb2VH1WS/**Image**/zurcUNUB45cNOVKYREke
* /tier1-apps-dev/quickstart/**Image**/9daDiwJsjqCzAI59cEI0
* /tier1-apps-dev/remote_vote/**User**/5faEiyKtjlDyBH34cT21


In the example:
* There are two Firestore Documents, representing apps,  under the root collection **tier1-apps-dev**  
  * /tier1-apps-dev/**quickstart**  
  * /tier1-apps-dev/**remote_vote**

When coding,  
* The quickstart app  has a total of 4 objects : one of class User, one of class WebSession, two of class Image.
* One of the quickstart Image objects (id=zurcUNUB45cNOVKYREke) is associated to a User object (id=w6lm7VRihyOGUb2VH1WS).
* The application objects are stored as Firestore Documents, members of the Firestore Collections 
  * /tier1-apps-dev/quickstart/User
  * /tier1-apps-dev/quickstart/WebSession
  * /tier1-apps-dev/quickstart/Image
  * /tier1-apps-dev/quickstart/User/w6lm7VRihyOGUb2VH1WS/Image


## Firestore performance considerations
 **Performance and scalability limitations for multi-tenancy in a single project**
   * There's a limit of read/writes per second for a Firestore instance (1 instance per project constraint)
   * Currently,  the limit is 10000 read/writes per second.
   * Read/writes for every scope in a project will count towards that limit

More information on [Firestore standard limits](https://cloud.google.com/firestore/quotas)