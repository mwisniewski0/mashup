import onedrive_cloud
import globals
import clouds
import sqlite3
import dropbox_cloud


clouds_manager = clouds.CloudsManager(sqlite3.connect('mashup_sql.db'))
class a:
    def __init__(self, cloud):
        self.clouds_manager = cloud
globals.add_resource('modules', a(clouds_manager))
# od = onedrive_cloud.OneDrive()
# od.authenticate(b'MCZUHE4zVd5jE15qim3zE8bxfAp2*!3gqe8vORYpdICU*EOsFFPeEr75lIGK*WYw3rHx3SH0lEa5xQc6dNS*rKiiGumGQaj8PpS96O4uEvI4whjFk1rmcCOy0LEDUWychkOuNMGFMs5QscbA*71rXmnfcS9xRuN2Mi7uBiDdozkgutJPevxYJSCCgyJdL5CVf9wZU2lH5dDUoM1DJvQLihl6gxReKhxknAqV5MRIa!k52EE3yh2CjgUyjpNFIlIa3WeSedPCzBOCr8MhDG*K5g1Ox86LWM!zBVLTBXQ3plSwfMNQtKhpheqOwaJRd87MgS5Doqxc9tSe54xN22pJNkV0Cm*v1kJAIU*UyTURHavKT')
# od.upload('file.txt', 'stuff')
# print(od.download('file.txt'))
# od.remove('file.txt')
# od.clean_mashup()

db = dropbox_cloud.Dropbox()
db.authenticate(b'UMElWsK27zAAAAAAAAAASTbdzh6mo0c3SSdZ4Irzs6uicwVHjjwtdaNI0Q4kLX8N')
db.clean_mashup()
db.prepare_mashup()
db.upload('file.txt', 'stuff')
print(db.download('file.txt'))
db.remove('file.txt')
db.clean_mashup()

