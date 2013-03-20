# Programmer: Chris Bunch (chris@appscale.com)


# General purpose library imports
import jinja2
import os
import re
import urllib
import webapp2


# Google App Engine API imports
from google.appengine.api import users


# Google App Engine Datastore-related imports
from google.appengine.ext import ndb


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
  s3_path: A reference to Amazon S3 that indicates where the file
    itself can be downloaded.
  description: An explanation of what the app does.
  download_count: The number of times that this application has been
    downloaded.
  size: The size of the file to download.
  owner: The user who uploaded the application.
  """
  s3_path = ndb.StringProperty()
  description = ndb.TextProperty()
  download_count = ndb.IntegerProperty()
  size = ndb.StringProperty()
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
  geopt: The location that the user has most recently logged in at.
  """
  uploaded_apps = ndb.StringProperty(repeated=True)
  downloaded_apps = ndb.StringProperty(repeated=True)
  ip_address = ndb.StringProperty()
  country = ndb.StringProperty()
  region = ndb.StringProperty()
  city = ndb.StringProperty()
  geopt = ndb.GeoPtProperty()


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
      template_values['size'] = app_metadata.size
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
      mark_app_as_downloaded_for_user(self.request, get_common_template_params(), app_id)
      app_metadata.download_count += 1
      app_metadata.put()
      self.redirect(str(app_metadata.s3_path))
    else:
      self.error(404)


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
    template_values["upload_url"] = '/upload-internal'
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


class EditPage(webapp2.RequestHandler):
  """EditPage provides users with routes letting them edit metadata
  about the items they've uploaded to this app.
  """


  def get(self, app_id):
    """Doing a GET on the EditPage should retrieve the current parameters
    for the given metadata and present them to the user for editing.
    """
    app_metadata = AppMetadata.get_by_id(app_id)
    template_values = get_common_template_params()
    template_values["app_id"] = app_id
    template_values["description"] = app_metadata.description
    template_values["size"] = app_metadata.size
    template_values["s3_path"] = app_metadata.s3_path
    template_values["upload_url"] = '/edit/' + app_id
    template = jinja_environment.get_template('templates/upload.html')
    self.response.out.write(template.render(template_values))


  def post(self, app_id):
    """Doing a POST on the EditPage should validate the parameters
    on the form provided by the GET Page, and then update the metadata
    stored via NDB.
    """
    # Get all the params from the form so that we can create a new
    # AppMetadata from it.
    # TODO(cgb): Validate these parameters (as well as the app itself)
    # and abort the upload process if they aren't there.
    description = self.request.get('description')
    s3_path = self.request.get('s3_path')

    # Create an AppMetadata object to keep track of the uploaded app
    # TODO(cgb): The put operation is not guaranteed to succeed.
    # Catch the exception it can throw if the Datastore is down and
    # act accordingly.
    app_metadata = AppMetadata.get_by_id(app_id)
    app_metadata.s3_path = s3_path
    app_metadata.description = description
    app_metadata.size = self.request.get('size')
    app_metadata.put()

    self.redirect('/upload-successful')


class UploadHandler(webapp2.RequestHandler):


  def post(self):
    """Doing a POST on the UploadPage should validate the parameters
    on the form provided by the GET page, and then store the
    application via the Blobstore.
    """
    # Get all the params from the form so that we can create a new
    # AppMetadata from it.
    # TODO(cgb): Validate these parameters (as well as the app itself)
    # and abort the upload process if they aren't there.
    appid = self.request.get('appid')
    description = self.request.get('description')
    s3_path = self.request.get('s3_path')

    # Create an AppMetadata object to keep track of the uploaded app
    # TODO(cgb): The put operation is not guaranteed to succeed.
    # Catch the exception it can throw if the Datastore is down and
    # act accordingly.
    app_metadata = AppMetadata(id = appid)
    app_metadata.s3_path = s3_path
    app_metadata.description = description
    app_metadata.download_count = 0
    app_metadata.size = self.request.get('size')
    app_metadata.owner = users.get_current_user()
    app_metadata.put()

    self.redirect('/upload-successful')


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

  app_metadata = AppMetadata.query().order(-AppMetadata.key)

  dict_metadata = []
  for app_metadatum in app_metadata:
    version = re.search("\d+.\d+.\d+", app_metadatum.key.id()).group()
    print "[" + version + "]"
    dict_metadata.append({
      "name" : app_metadatum.key.id(),
      "download_count" : app_metadatum.download_count,
      "size" : app_metadatum.size,
      "version" : version
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


def mark_app_as_downloaded_for_user(request, user_info, app_id):
  """Records the given application as 'downloaded' for the
  currently logged in user.

  Args:
    app_id: The application ID (and a key into AppsMetadata)
      that we should note that the user has downloaded.
  """
  if user_info['is_logged_in']:
    email = user_info['user_name']
  else:
    email = request.remote_addr

  user_metadata = UserMetadata.get_by_id(email)
  if not user_metadata:
    user_metadata = UserMetadata(id = email)
    user_metadata.uploaded_apps = []
    user_metadata.downloaded_apps = []

  user_metadata.ip_address = request.remote_addr
  user_metadata.country = request.headers.get('X-AppEngine-Country')
  user_metadata.region = request.headers.get('X-AppEngine-Region')
  user_metadata.city = request.headers.get('X-AppEngine-City')

  location = request.headers.get('X-AppEngine-CityLatLong')
  if location:
    user_metadata.geopt = ndb.GeoPt(location)
  else:
    user_metadata.geopt = None

  user_metadata.downloaded_apps.append(app_id)
  user_metadata.put()


# Start up our app
app = webapp2.WSGIApplication([
  ('/', MainPage),
  ('/apps/(.+)', AppsPage),
  ('/download/(.+)', DownloadPage),
  ('/edit/(.+)', EditPage),
  ('/upload', UploadPage),
  ('/upload-internal', UploadHandler),
  ('/upload-successful', UploadSuccessfulPage)
], debug=True)
