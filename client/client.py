import http_helpers
import json
import abc
import fs_client
from getpass import getpass


def separator():
    return '---------------------------------------------------'

class MenuEntry(metaclass=abc.ABCMeta):
    def __init__(self, title):
        self.title = title

    @abc.abstractmethod
    def act(self, common_data):
        return None


class MenuTransitioner(MenuEntry):
    def __init__(self, title, next_menu):
        super().__init__(title)
        self.next_menu = next_menu

    def act(self, common_data):
        return self.next_menu


class CloudsViewEntry(MenuEntry):
    def __init__(self, title):
        super().__init__(title)

    def act(self, common_data):
        response = http_helpers.auth_http_req(common_data['conn'],common_data['session_id'], "GET", "/clouds/list")
        print(response)
        # response = json.loads(response)
        # table = [['id', 'name', 'type', 'taken', 'quota', 'percent taken']]
        # for row in response:
        #     table.append([row['id'], row['name'], row['taken'], row['quota'], row['taken']/row['quota'] * 100])
        #
        # longest_name_length = max([len(row['name'])])
        # for row in table:
        #     print_row = "{:10s} {:3d}  {:7.2f}".format()
        return None


class LoginEntry(MenuEntry):
    def __init__(self, title, main_menu):
        super().__init__(title)
        self.main_menu = main_menu

    def act(self, common_data):
        print('Login form\n' + separator())

        session_id = None
        while session_id is None:
            username = input('Username (leave blank to exit this menu): ')
            if username == '':
                return None

            password = input('Password: ')
            request_body = {'username': username, 'password': password}
            try:
                response = http_helpers.http_req(common_data['conn'], "POST", "/login", json.dumps(request_body))
                session_id = json.loads(response)['session_id']
            except Exception as e:
                print(e.args[1])
                print('Try again')
        common_data['session_id'] = session_id
        return self.main_menu

class FSEntry(MenuEntry):
    def __init__(self, title):
        super().__init__(title)

    def act(self, common_data):
        fs_client.FileSystemClient(common_data['conn'], common_data['session_id']).run()

class AddCloudEntry(MenuEntry):
    def __init__(self, title, cloud_resource):
        super().__init__(title)
        self.cloud_resource = cloud_resource

    def act(self, common_data):
        print('Adding a cloud\n' + separator())

        session_id = common_data['session_id']
        connection = common_data['conn']
        try:
            response = http_helpers.auth_http_req(connection, session_id, "POST","/clouds/"+self.cloud_resource+"/auth_info")
            authorize_uri = json.loads(response)['authorize_uri']
            print("To authorize the request, visit: " + authorize_uri)
            input("Press [Enter] to continue...")
        except Exception:
            print("Something went wrong with the request, sorry!")

        return None

class ExitEntry(MenuEntry):
    def __init__(self, title):
        super().__init__(title)

    def act(self, common_data):
        common_data['exit'] = 1
        return None

class LogoutEntry(MenuEntry):
    def __init__(self, title, previous_menu):
        super().__init__(title)
        self.previous_menu = previous_menu

    def act(self, common_data):
        # TODO: send logout request
        del common_data['session_id']
        return self.previous_menu


class Menu:
    def __init__(self, title, menu_entries = None):
        self.title = title
        self.entries = menu_entries

    def set_menu_entries(self, menu_entries):
        self.entries = menu_entries

    def execute(self, common_data):
        valid = False
        entry = None

        while not valid:
            print("\n\n"+self.title+"\n"+separator())
            for i in range(len(self.entries)):
                print(str(i+1) + ". " + self.entries[i].title)
            print("")
            choice = input("Select entry: ")

            try:
                choice = int(choice)
                entry = self.entries[choice-1]
                valid = True
            except Exception:
                print("Invalid entry, try again")

        return entry.act(common_data)

class Client:
    def __init__(self, address):
        self.conn = http_helpers.start_connection("https://localhost:8080")
        self.common_data = {'conn': self.conn}
        self.prepare_menus()
        self.current_menu = self.menus['login']

    def prepare_login_menu(self):
        entries = []
        entries.append(LoginEntry('Log in', self.menus['main']))
        entries.append(ExitEntry('Exit'))
        self.menus['login'].set_menu_entries(entries)

    def prepare_main_menu(self):
        entries = []
        entries.append(FSEntry('Access file system'))
        entries.append(MenuTransitioner('Manage clouds', self.menus['clouds']))
        entries.append(MenuTransitioner('Account settings', None))
        entries.append(LogoutEntry('Log out', self.menus['login']))
        self.menus['main'].set_menu_entries(entries)

    def prepare_clouds_menu(self):
        entries = []
        entries.append(AddCloudEntry('Dropbox', 'dropbox'))
        entries.append(AddCloudEntry('OneDrive', 'onedrive'))
        entries.append(MenuTransitioner('Back', self.menus['clouds']))
        self.menus['add_cloud'] = Menu('Add a cloud', entries)

        entries = []
        entries.append(CloudsViewEntry('View clouds'))
        entries.append(MenuTransitioner('Add a cloud', self.menus['add_cloud']))
        entries.append(MenuTransitioner('Remove a cloud', None))
        entries.append(MenuTransitioner('Back', self.menus['main']))
        self.menus['clouds'].set_menu_entries(entries)

    def prepare_menus(self):
        self.menus = {}

        self.menus['login'] = Menu('Start menu')
        self.menus['main'] = Menu('Main menu')
        self.menus['clouds'] = Menu('Cloud management')

        self.prepare_login_menu()
        self.prepare_main_menu()
        self.prepare_clouds_menu()

    def run(self):
        print('This is MashUp 0.1')
        print(separator())
        while 'exit' not in self.common_data:
            result = self.current_menu.execute(self.common_data)
            if result is not None:
                self.current_menu = result

if __name__ == '__main__':
    client = Client("https://localhost:8080")
    client.run()