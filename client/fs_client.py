import http_helpers
import os
import json
import shlex
import traceback


def separator():
    return '---------------------------------------------------'

class FileSystemClient:
    def __init__(self, connection, session_id):
        self.conn = connection
        self.ses_id = session_id
        self.start_dir = os.getcwd()
        self.cur_dir = []
        self.mode = 'r'

    def get_cur_dir_string(self):
        return "/" + "/".join(self.cur_dir)

    def get_prompt(self):
        if self.mode == 'r':
            return "[remote] " + self.get_cur_dir_string() + "> "
        else:
            return "[local] " + os.getcwd() + "> "

    def ls(self, args):
        folders = []
        files = []

        if self.mode == 'l':
            for item in os.listdir(os.getcwd()):
                if os.path.isdir(item):
                    folders.append(item)
                else:
                    files.append(item)
        else:
            response = http_helpers.auth_http_req(self.conn, self.ses_id, "GET", "/files" + self.get_cur_dir_string())
            children = json.loads(response)['children']
            folders = [child['name'] for child in children if child['type'] == 'folder']
            files = [child['name'] for child in children if child['type'] == 'file']

        for folder in folders:
            print(folder + "/")
        for file in files:
            print(file)
        if len(folders) == 0 and len(files) == 0:
            print('--- This catalog is empty ---')

    def transform_path(self, original_path, new):
        path_segments = new.split('/')
        if path_segments[0] == '':
            output_path = []
        else:
            output_path = original_path[:]

        for segment in path_segments:
            if segment == '':
                continue
            elif segment == '.':
                continue
            elif segment == '..':
                output_path = output_path[:len(output_path) - 1]
            else:
                output_path.append(segment)
        return output_path

    def cd(self, args):
        if self.mode == 'l':
            try:
                if len(args) > 0:
                    os.chdir(args[0])
                else:
                    os.chdir("/")
            except Exception as e:
                print('Invalid path. Try again')
        else:
            if len(args) > 0:
                new_path = self.transform_path(self.cur_dir, args[0])

                # check if path is a folder. If it's not, exception will be thrown
                data, response = http_helpers.auth_http_req(self.conn, self.ses_id, "GET", "/files/" + "/".join(new_path),
                                                     None, {'length': 0}, {}, True)
                if response.status >= 300:
                    print('Invalid path. Try again')
                    return
                if response.getheader('X_FILE_SIZE') is not None:
                    print('Invalid path. Try again')
                    return

                self.cur_dir = new_path
            else:
                self.cur_dir = []

    def print_progress_bar(self, fraction, size):
        full_count = int(fraction * size)
        empty_count = size - full_count
        print("\r["+'-'*full_count + ' '*empty_count + '] ' + str(int(fraction*100))+"%" , end="")

    def rm(self, args):
        if len(args) == 0:
            print('You need to specify the path to file')
            return
        if self.mode == 'l':
            try:
                os.remove(args[0])
            except Exception:
                print("Could not remove the item")
        else:
            remote_path = self.transform_path(self.cur_dir, args[0])
            if remote_path[0] == '':
                remote_path = remote_path[1:]
            try:
                http_helpers.auth_http_req(self.conn, self.ses_id, "DELETE", "files/" + "/".join(remote_path))
            except Exception as e:
                print('Removal failed')
                if len(e.args) >= 2:
                    print('Information from the service: ', e.args[1])

    def mkdir(self, args):
        if len(args) == 0:
            print('You need to specify the path for the catalog')
            return
        if self.mode == 'l':
            try:
                os.mkdir(args[0])
            except Exception:
                print("Could not create the catalog")
        else:
            remote_path = self.transform_path(self.cur_dir, args[0])
            if remote_path[0] == '':
                remote_path = remote_path[1:]
            try:
                http_helpers.auth_http_req(self.conn, self.ses_id, "PUT", "files/" + "/".join(remote_path),None,
                                           {'item_type':'folder'})
            except Exception as e:
                print('Directory creation failed')
                if len(e.args) >= 2:
                    print('Information from the service: ', e.args[1])

    def mv(self, args):
        if len(args) < 2:
            print('You need to specify both from and to path')
            return
        if self.mode == 'l':
            try:
                os.rename(args[0], args[1])
            except Exception:
                print("Could not move the item")
        else:
            from_path = self.transform_path(self.cur_dir, args[0])
            to_path = self.transform_path(self.cur_dir, args[1])
            if from_path[0] == '':
                from_path = from_path[1:]
            if to_path[0] == '':
                to_path = to_path[1:]
            try:
                http_helpers.auth_http_req(self.conn, self.ses_id, "PUT", "files/" + "/".join(to_path),
                                           "/".join(from_path), {'item_type':'other_item'})
            except Exception as e:
                print('Moving failed')
                if len(e.args) >= 2:
                    print('Information from the service: ', e.args[1])

    def fetch(self, args):
        if len(args) == 0:
            print('You need to specify the remote path to file')
        else:
            remote_path = self.transform_path(self.cur_dir, args[0])
            local_path = os.getcwd().split('/')
            if len(args) > 1:
                local_path = self.transform_path(local_path, args[1])
            else:
                local_path = self.transform_path(local_path, remote_path[len(remote_path)-1])
            if remote_path[0] == '':
                remote_path = remote_path[1:]
            if local_path[0] == '':
                local_path = local_path[1:]

            data, response = http_helpers.auth_http_req(self.conn, self.ses_id, "GET", "files/"+"/".join(remote_path),None,
                                                        {'start': 0, 'length': 0},{},True)
            if response.status == 404:
                print("Remote file does not exist")
                return
            if response.status >= 300:
                print("Something went wrong. Information from the service:")
                print(data.decode('utf-8'))
                return
            try:
                file_size = int(response.getheader("X_FILE_SIZE"))
            except Exception:
                print("Provided remote path is a folder - not a file")
                return
            try:
                with open("/"+"/".join(local_path), "wb") as f:
                    current_start = 0
                    length = 2 ** 22
                    print("Starting the download. File size: " + str(file_size) + " bytes")
                    while current_start < file_size:
                        self.print_progress_bar(current_start/file_size, 20)
                        data, response = http_helpers.auth_http_req(self.conn, self.ses_id, "GET",
                                                          "files/" + "/".join(remote_path), None,
                                                          {'start': current_start, 'length': length},{}, True)
                        if response.status >= 300:
                            print("\rFetch failed")
                            return

                        f.write(data)
                        current_start += length
                print("\rFile fetched")
            except Exception as e:
                print("Could not open the file to write")
                if len(e.args) > 1:
                    print(e.args[1])

    def store(self, args):
        if len(args) == 0:
            print('You need to specify the local path to file')
        else:
            local_path = os.getcwd().split('/')
            local_path = self.transform_path(local_path, args[0])
            remote_path = self.cur_dir[:]
            if len(args) > 1:
                remote_path = self.transform_path(remote_path, args[1])
            else:
                remote_path = self.transform_path(remote_path, local_path[len(local_path)-1])
            if remote_path[0] == '':
                remote_path = remote_path[1:]
            if local_path[0] == '':
                local_path = local_path[1:]

            try:
                with open("/"+"/".join(local_path), "rb") as f:
                    f.seek(0, 2) # move the cursor to the end of the file
                    size = f.tell()
                    f.seek(0)

                    chunk = 2 ** 18
                    while f.tell() != size:
                        self.print_progress_bar(f.tell() / size, 20)
                        data = f.read(chunk)
                        http_helpers.auth_http_req(self.conn, self.ses_id, "PUT", "files/" + "/".join(remote_path),
                                                   data, {'session_action': 'add', 'item_type': 'file'})

                    http_helpers.auth_http_req(self.conn, self.ses_id, "PUT", "files/" + "/".join(remote_path),
                                               b'', {'session_action': 'end', 'item_type': 'file'})
                    print('\rUpload finished')
            except Exception:
                #traceback.print_exc()
                print("\rUpload failed")

    def print_help_string(self):
        print("Available commands:\n"
              "l - switch to local mode and perform cd and ls locally\n"
              "r - switch to remote mode and perform cd, ls and rm remotely\n"
              "cd <path> - change current directory to <path>\n"
              "ls - list contents of the current catalog\n"
              "rm <path> - removes the item at <path>\n"
              "mv <from> <to> - moves an item at <from> to <to>\n"
              "fetch <remote_path> <local_path> - download file from <remote_path> to <local_path>\n"
              "                                   if <local_path> is omitted, current directory is assumed\n"
              "store <local_path> <remote_path> - upload file from <local_path> to <remote_path>\n"
              "                                   if <remote_path> is omitted, current directory is assumed\n"
              "exit - exits the file system console\n")

    def run(self):
        done = False
        while not done:
            command = input(self.get_prompt())
            args = shlex.split(command)
            if len(args) == 0:
                continue
            else:
                command = args[0]
                args = args[1:]
                if command.lower() == 'l':
                    self.mode = 'l'
                elif command.lower() == 'r':
                    self.mode = 'r'
                elif command.lower() == 'ls':
                    self.ls(args)
                elif command.lower() == 'cd':
                    self.cd(args)
                elif command.lower() == 'rm':
                    self.rm(args)
                elif command.lower() == 'mkdir':
                    self.mkdir(args)
                elif command.lower() == 'mv':
                    self.mv(args)
                elif command.lower() == 'fetch':
                    self.fetch(args)
                elif command.lower() == 'store':
                    self.store(args)
                elif command.lower() == 'help':
                    self.print_help_string()
                elif command.lower() == 'exit':
                    done = True
                else:
                    print('Invalid command. Try command: help')
        os.chdir(self.start_dir)