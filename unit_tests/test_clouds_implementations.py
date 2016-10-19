import onedrive_cloud
import dropbox_cloud
import globals
import clouds
import sqlite3
from exceptions import *
from unit_tests.abstract_mashup_unittest import MashupUnitTest


class CloudImplementationTest:
    def test_upload_download(self):
        self.cloud.upload('file.txt', 'stuff')
        self.assertEqual(self.cloud.download('file.txt'), b'stuff')

    def test_nonexistent_download(self):
        accepted = False
        try:
            self.cloud.download("Some nonexistent file")
            accepted = True
        except MashupCloudOperationException:
            accepted = False
        self.assertFalse(accepted)

    def test_nonexistent_remove(self):
        accepted = False
        try:
            self.cloud.remove("Some nonexistent file")
            accepted = True
        except MashupCloudOperationException:
            accepted = False
        self.assertFalse(accepted)

    def test_replace(self):
        self.cloud.upload('file.txt', 'stuff')
        self.cloud.upload('file.txt', 'stuff2')
        self.assertEqual(self.cloud.download('file.txt'), b'stuff2')

    def test_exist(self):
        self.assertFalse(self.cloud.exists("file.txt"))
        self.cloud.upload('file.txt', 'stuff')
        self.assertTrue(self.cloud.exists("file.txt"))

    def test_remove(self):
        self.cloud.upload('file.txt', 'stuff')
        self.cloud.remove('file.txt')
        self.assertFalse(self.cloud.exists("file.txt"))

class OneDriveImplementationTest(MashupUnitTest, CloudImplementationTest):
    def tearDown(self):
        self.cloud.clean_mashup()
        globals.remove_resource('modules')

    def setUp(self):
        class a:
            def __init__(self, cloud):
                self.clouds_manager = cloud

        clouds_manager = clouds.CloudsManager(sqlite3.connect('mashup_sql.db'))
        globals.add_resource('modules', a(clouds_manager))
        self.cloud = onedrive_cloud.OneDrive()
        self.cloud.authenticate(
            b'MCZUHE4zVd5jE15qim3zE8bxfAp2*!3gqe8vORYpdICU*EOsFFPeEr75lIGK*WYw3rHx3SH0lEa5xQc6dNS*rKiiGumGQaj8PpS96O4uEvI4whjFk1rmcCOy0LEDUWychkOuNMGFMs5QscbA*71rXmnfcS9xRuN2Mi7uBiDdozkgutJPevxYJSCCgyJdL5CVf9wZU2lH5dDUoM1DJvQLihl6gxReKhxknAqV5MRIa!k52EE3yh2CjgUyjpNFIlIa3WeSedPCzBOCr8MhDG*K5g1Ox86LWM!zBVLTBXQ3plSwfMNQtKhpheqOwaJRd87MgS5Doqxc9tSe54xN22pJNkV0Cm*v1kJAIU*UyTURHavKT')
        self.cloud.prepare_mashup()

class DropboxImplementationTest(MashupUnitTest, CloudImplementationTest):
    def tearDown(self):
        self.cloud.clean_mashup()
        globals.remove_resource('modules')

    def setUp(self):
        class a:
            def __init__(self, cloud):
                self.clouds_manager = cloud

        clouds_manager = clouds.CloudsManager(sqlite3.connect('mashup_sql.db'))
        globals.add_resource('modules', a(clouds_manager))
        self.cloud = dropbox_cloud.Dropbox()
        self.cloud.authenticate(b'UMElWsK27zAAAAAAAAAASTbdzh6mo0c3SSdZ4Irzs6uicwVHjjwtdaNI0Q4kLX8N')
        self.cloud.prepare_mashup()


