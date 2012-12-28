# Programmer: Chris Bunch (chris@appscale.com)


# General purpose library imports
import jinja2
import os
import urllib
import webapp2


# Google App Engine API imports
from google.appengine.api import users


# Google App Engine Datastore-related imports
from google.appengine.ext import blobstore
from google.appengine.ext import ndb
from google.appengine.ext.webapp import blobstore_handlers


# Set up Jinja to read template files for our app
jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


# The maximum number of applications that a single user can upload
# to FileHosting.
MAXIMUM_APPS_UPLOADED_PER_USER = 100


class AppMetadata(ndb.Model):
  """AppMetadata represents information about the applications that
  FileHosting provides access to. Specific fields include:

  name: The user-provided name of the application. This is the key
    of the item, to avoid having to manually index it.
  blob_key: A reference to Blobstore that indicates where the app
    itself can be downloaded.
  description: An explanation of what the app does.
  download_count: The number of times that this application has been
    downloaded.
  owner: The user who uploaded the application.
  """
  blob_key = ndb.StringProperty()
  description = ndb.TextProperty()
  download_count = ndb.IntegerProperty()
  owner = ndb.UserProperty()


class UserMetadata(ndb.Model):
  """UserMetadata represents information about the users who upload
  and download apps via FileHosting. Specific fields include:

  email: The user's e-mail address. This is the key of the item, to
    avoid having to manually index it.
  uploaded_apps: A list of applications that the user has uploaded.
    Individual items are keys to AppMetadata objects.
  downloaded_apps: A list of applications that the user has downloaded.
    Individual items are keys to AppMetadata objects.
  ip_address: The IP address that the user has most recently logged in
    with.
  country: The country that App Engine believes the user originates from.
  region: The name of the region that App Engine believes the user
    originates from.
  city: The name of the city that App Engine believes the user originates
    from.
  geolocation: The location that the user has most recently logged in at.
  """
  uploaded_apps = ndb.StringProperty(repeated=True)
  downloaded_apps = ndb.StringProperty(repeated=True)
  ip_address = ndb.StringProperty()
  country = ndb.StringProperty()
  region = ndb.StringProperty()
  city = ndb.StringProperty()
  geolocation = ndb.GeoPtProperty()


class MainPage(webapp2.RequestHandler):
  """MainPage represents the landing page that users first come to
  when they access FileHosting. It should list all of the
  applications that we are hosting under some default sort order,
  and enable users to change the sort order for some reasonable
  sort orders.
  """


  def get(self):
    """Doing a GET on the main page requests data on all of the apps
    that we're hosting, and lets users log in if they desire.
    """
    template_values = get_common_template_params()
    template_values["app_metadata"] = get_hosted_app_metadata()
    template = jinja_environment.get_template('templates/index.html')
    self.response.out.write(template.render(template_values))


class AppsPage(webapp2.RequestHandler):
  """AppsPage provides users with information about an application.
  """


  def get(self, app_id):
    template_values = get_common_template_params()

    app_metadata = AppMetadata.get_by_id(app_id)
    if app_metadata:
      template_values['app_id'] = app_id
      template_values['description'] = app_metadata.description
      template_values['download_count'] = app_metadata.download_count
      template_values['owner'] = app_metadata.owner.nickname()
    else:
      # TODO(cgb): Find out what we should do if the app_id doesn't
      # exist, and how to format the apps template page.
      pass

    template = jinja_environment.get_template('templates/apps.html')
    self.response.out.write(template.render(template_values))


class DownloadPage(webapp2.RequestHandler):
  """DownloadPage provides a nice pretty link that can be referenced
  to download hosted applications. It also lets us manage the download
  count programmatically.
  """
    

  def get(self, app_id):
    app_metadata = AppMetadata.get_by_id(app_id)
    if app_metadata:
      mark_app_as_downloaded_for_user(get_common_template_params(), app_id)
      app_metadata.download_count += 1
      app_metadata.put()
      self.redirect('/serve/%s' % app_metadata.blob_key)
    else:
      # TODO(cgb): Find out how to write a 404 here.
      pass


class UploadPage(webapp2.RequestHandler):
  """UploadPage provides users with a way to upload their applications.
  We currently don't actually validate what the user sends to us, so
  we really could be hosting anything.
  """


  def get(self):
    """A GET on the UploadPage should provide users with a form that
    they can fill out to upload their application to us, which will
    then send this info to the POST route.
    """
    template_values = get_common_template_params()
    template_values["upload_url"] = blobstore.create_upload_url('/upload-internal')
    template = jinja_environment.get_template('templates/upload.html')
    self.response.out.write(template.render(template_values))


class UploadSuccessfulPage(webapp2.RequestHandler):
  """UploadSuccessfulPage provides users with a page that tells them
  that we were able to host their application for them.
  """


  def get(self):
    template_values = get_common_template_params()
    template = jinja_environment.get_template('templates/upload_successful.html')
    self.response.out.write(template.render(template_values))


class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):


  def post(self):
    """Doing a POST on the UploadPage should validate the parameters
    on the form provided by the GET page, and then store the
    application via the Blobstore.
    """
    upload_files = self.get_uploads('file')
    blob_info = upload_files[0]

    # Get all the params from the form so that we can create a new
    # AppMetadata from it.
    # TODO(cgb): Validate these parameters (as well as the app itself)
    # and abort the upload process if they aren't there.
    appid = self.request.get('appid')
    description = self.request.get('description')

    # Create an AppMetadata object to keep track of the uploaded app
    # TODO(cgb): The put operation is not guaranteed to succeed.
    # Catch the exception it can throw if the Datastore is down and
    # act accordingly.
    app_metadata = AppMetadata(id = appid)
    app_metadata.blob_key = str(blob_info.key())
    app_metadata.description = description
    app_metadata.download_count = 0
    app_metadata.owner = users.get_current_user()
    app_metadata.put()

    self.redirect('/upload-successful')


class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
  """ServeHandler is a piece of boilerplate code that stores uploaded
  applications in Blobstore, for later retrieval.
  """


  def get(self, resource):
    """Stores the named file in the Blobstore for later use.
    """
    resource = str(urllib.unquote(resource))
    blob_info = blobstore.BlobInfo.get(resource)
    self.send_blob(blob_info)


def get_hosted_app_metadata():
  """get_hosted_app_metadata queries the Datastore for metadata
  about the applications that FileHosting hosts. It returns this
  data as a dict that can be dumped via JSON, enabling it to be
  easily used by our app in a RESTful manner.
  """
  # TODO(cgb): Consider not querying the entire datastore, as it
  # could return a lot of results. A cursor should then be stored
  # in the returned data and hoarded carefully from users (since it
  # is a potential security risk).

  app_metadata = AppMetadata.query()

  dict_metadata = []
  for app_metadatum in app_metadata:
    dict_metadata.append({
      "name" : app_metadatum.key.id(),
      "download_count" : app_metadatum.download_count
    })

  return dict_metadata


def get_common_template_params():
  """Returns a dict of params that are commonly used by our
  templates, including information about the currently logged in
  user.
  """
  user = users.get_current_user()
  if user:
    is_logged_in = True
    is_admin = users.is_current_user_admin()
    user_name = user.nickname()
  else:
    is_logged_in = False
    is_admin = False
    user_name = ""

  return {
    "is_logged_in" : is_logged_in,
    "is_admin" : is_admin,
    "user_name" : user_name,
    "login_url" : users.create_login_url("/"),
    "logout_url" : users.create_logout_url("/")
  }


def mark_app_as_downloaded_for_user(user_info, app_id):
  """Records the given application as 'downloaded' for the
  currently logged in user.

  Args:
    app_id: The application ID (and a key into AppsMetadata)
      that we should note that the user has downloaded.
  """
  if not user_info['is_logged_in']:
    raise Exception()

  email = user_info['user_name']
  user_metadata = UserMetadata.get_by_id(email)
  if not user_metadata:
    user_metadata = UserMetadata(id = email)
    user_metadata.uploaded_apps = []
    user_metadata.downloaded_apps = []

  user_metadata.downloaded_apps.append(app_id)
  user_metadata.put()


def update_user_location(request):
  """Uses information from the given HTTP request to learn
  where the user is, and updates the Datastore with this
  information.

  Args:
    request: The HTTP request sent by the user's browser,
      which includes the HTTP headers that identify the
      user.
  """
  user_metadata.ip_address = request.get('REMOTE_ADDR')
  user_metadata.country = request.get('X-AppEngine-Country')
  user_metadata.region = request.get('X-AppEngine-Region')
  user_metadata.city = request.get('X-AppEngine-City')
  user_metadata.geolocation = request.get('X-AppEngine-CityLatLong')


# Start up our app
app = webapp2.WSGIApplication([
  ('/', MainPage),
  ('/apps/(.+)', AppsPage),
  ('/download/(.+)', DownloadPage),
  ('/upload', UploadPage),
  ('/upload-internal', UploadHandler),
  ('/upload-successful', UploadSuccessfulPage),
  ('/serve/([^/]+)?', ServeHandler)
], debug=True)
