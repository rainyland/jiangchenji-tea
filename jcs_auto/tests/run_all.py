import unittest, sys
from test_copy_engine import TestCopyEngine
from test_image_pipeline import TestImagePipeline
from test_risk_control import TestRiskControl, TestScheduler
suite = unittest.TestSuite()
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestCopyEngine))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestImagePipeline))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestRiskControl))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(TestScheduler))
runner = unittest.TextTestRunner(verbosity=1)
r = runner.run(suite)
sys.exit(0 if r.wasSuccessful() else 1)
