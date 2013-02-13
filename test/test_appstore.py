#!/usr/bin/env python
# Programmer: Chris Bunch (chris@appscale.com)


# General-purpose Python library imports
import unittest


# Google App Engine library imports
from google.appengine.ext import testbed


# AppStore import, the library that we're testing here
import appstore


class TestAppStore(unittest.TestCase):


  def setUp(self):
    self.testbed = testbed.Testbed()
    self.testbed.activate()
    self.testbed.init_datastore_v3_stub()
    self.testbed.init_memcache_stub()


  def tearDown(self):
    self.testbed.deactivate()


  def get_fake_app_metadata(self, name):
    return appstore.AppMetadata(id = name)


  def get_fake_user_metadata(self, name):
    return appstore.UserMetadata(id = name)

  
  def get_fake_user_info(self, user_db):
    return {
      "is_logged_in" : True,
      "user_name" : user_db.key.id(),
      "login_url" : "/login",
      "logout_url" : "/logout"
    }


  def testGetHostedAppMetadata(self):
    # here, we want to test and see if get_hosted_app_metadata properly
    # queries the Datastore. let's say we have two entities in there
    # right now

    app1 = self.get_fake_app_metadata("one")
    app2 = self.get_fake_app_metadata("two")

    app1.put()
    app2.put()

    actual = appstore.get_hosted_app_metadata()
    self.assertEqual("one", actual[0]['name'])
    self.assertEqual("two", actual[1]['name'])


  def testMarkAppAsDownloadedForUser(self):
    # here, we want to test and see if mark_app_as_downloaded_for_user
    # properly uses the Datastore to note when users download apps. 
    # let's say we have three users in there right now
    
    user1 = self.get_fake_user_metadata("one")
    user2 = self.get_fake_user_metadata("two")
    user3 = self.get_fake_user_metadata("three")

    user1.put()
    user2.put()
    user3.put()

    # get some fake user data so that we can impersonate each user
    # we want to save data for
    user1_info = self.get_fake_user_info(user1)
    user2_info = self.get_fake_user_info(user2)
    user3_info = self.get_fake_user_info(user3)

    # now that we have the users in the DB, let's suppose that
    # users one and two download an app
    appstore.mark_app_as_downloaded_for_user(user1_info, "app1")
    appstore.mark_app_as_downloaded_for_user(user2_info, "app1")

    # and suppose that user three downloads a different app
    appstore.mark_app_as_downloaded_for_user(user3_info, "app2")

    # make sure the counts are all correctly tabulated
    user1_from_db = appstore.UserMetadata.get_by_id("one")
    self.assertEqual(["app1"], user1_from_db.downloaded_apps)

    user2_from_db = appstore.UserMetadata.get_by_id("two")
    self.assertEqual(["app1"], user2_from_db.downloaded_apps)

    user3_from_db = appstore.UserMetadata.get_by_id("three")
    self.assertEqual(["app2"], user3_from_db.downloaded_apps)


  def testMarkAppAsDownloadedForUserWhenNotLoggedIn(self):
    # if we try to mark apps as downloaded for a user when they
    # aren't logged in, that should throw an exception
    user_data = { "is_logged_in" : False }
    self.assertRaises(Exception,
      appstore.mark_app_as_downloaded_for_user, user_data, "app")
