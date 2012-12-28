require 'rubygems'
require 'rake'


# The location where the App Engine SDK is located on this machine.
# Clearly this doesn't work on non-Macs - see the TODO in the test
# task for some ideas on how to get around this.
SDK_PATH = "/Applications/GoogleAppEngineLauncher.app/Contents/Resources/GoogleAppEngine-default.bundle/Contents/Resources/google_appengine/"


task :coverage do |t|
  # Generates code coverage statistics if coverage.py is installed
  if `which coverage`.empty?
    abort("coverage.py isn't installed on this machine, so we can't " +
      "generate code coverage information. You can install coverage.py " +
      "by running the following command:\neasy_install coverage")
  end

  # Generate the code coverage stats (in HTML)
  ENV['PYTHONPATH'] = "#{File.dirname(__FILE__)}:#{SDK_PATH}"
  sh "coverage run test/test_suite.py"
  sh "coverage html --include appstore.py"
  sh "rm -rf coverage"
  sh "mv htmlcov coverage"

  # And print out that same info to the screen for the user to read
  sh "coverage report -m"
  puts "Done generating code coverage information!"
end


task :doc do |t|
  # Generates documentation
  # TODO(cgb): Figure out how to use "pydoc" to do this.
  # Consider "pydoc -w".
end


task :test do |t|
  # Runs tests
  # First, set up our PYTHONPATH so that we can import the files
  # we want to test. It should include at least the current directory
  # and the location where the Google App Engine SDK is located.
  # TODO(cgb): Try to find a better way to indicate where the SDK
  # is located - maybe via command-line argument?
  ENV['PYTHONPATH'] = "#{File.dirname(__FILE__)}:#{SDK_PATH}"
  sh "python test/test_suite.py"
  puts "Done running unit test suite!"
end


task :release => [:coverage, :doc, :test] do |t|
  # TODO(cgb): does a "release" consist of anything asides from the
  # above dependencies?
end
