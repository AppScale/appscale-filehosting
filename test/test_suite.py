#!/usr/bin/env python
# Programmer: Chris Bunch (chris@appscale.com)


# Before running any tests, make sure that all third-party libraries
# required by Google App Engine are installed.
try:
  import yaml
except ImportError:
  raise Exception("\n\nThe YAML library is required by Google App Engine " +
    "but is not installed on this machine. Install it from " +
    "http://pyyaml.org/\n")


import unittest


from test_appstore import TestAppStore


suite_appstore = unittest.TestLoader().loadTestsFromTestCase(TestAppStore)
all_tests = unittest.TestSuite([suite_appstore])
unittest.TextTestRunner(verbosity=2).run(all_tests)
