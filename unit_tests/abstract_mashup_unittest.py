import unittest


class MashupUnitTest(unittest.TestCase):
    def assert_400(self, statement):
        error_code_start = 2
        try:
            statement()
        except Exception as e:
            error_code_start = e.args[1][0]
        self.assertEqual(error_code_start, '4')