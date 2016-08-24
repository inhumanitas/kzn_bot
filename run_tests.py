# coding: utf-8

import unittest
import sys

suite = unittest.TestLoader().discover(start_dir='.', pattern='test_*.py')
runner = unittest.TextTestRunner(verbosity=2).run(suite)

sys.exit(int(not runner.wasSuccessful()))
