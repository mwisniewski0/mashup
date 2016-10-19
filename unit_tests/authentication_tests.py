from unit_tests.abstract_mashup_unittest import MashupUnitTest
import os
import subprocess
import http_helpers
import json
import time


class AuthenticationTests(MashupUnitTest):
    @classmethod
    def setUpClass(cls):
        cls.p = subprocess.Popen(["python3", "program.py", "gunicorn", "-sqlfile", "unit_test_db.db",
                              "-certfile","server.crt","-keyfile", "server.key"], cwd="../")
        # let the process start
        time.sleep(6)

    def test_register(self):
        request_body = {'username': 'user', 'password': 'pass'}
        http_helpers.http_req("https://localhost:8080", "POST", "/register", request_body)

    def test_register_illegal_characters(self):
        def test():
            request_body = {'username': 'user:::', 'password': 'pass'}
            http_helpers.http_req("https://localhost:8080", "POST", "/register", request_body)
        self.assert_400(test)

    def test_register_name_taken(self):
        request_body = {'username': 'john', 'password': 'doe'}
        http_helpers.http_req("https://localhost:8080", "POST", "/register", request_body)

        def test():
            request_body = {'username': 'john', 'password': 'jojo'}
            http_helpers.http_req("https://localhost:8080", "POST", "/register", request_body)
        self.assert_400(test)

    def test_short_name_register(self):
        # name too short
        def test():
            request_body = {'username': 'ja', 'password': 'doe'}
            http_helpers.http_req("https://localhost:8080", "POST", "/register", request_body)
        self.assert_400(test)

    def test_long_name_register(self):
        # name too long
        def test():
            request_body = {'username': 'jagfdlkagdajfghaeirogjreoigjnaerokgjnafdokgjadfokgjdafkgjadflkgjadflkgjadflkgjfdalkgjdafklgjadflkgjafdlkgjafdlkgjdalkgjadflkgjaldkfgjlkfdagjlkfadjglkadjglkadfgjakdlfjglkadfgjalfdkgjkaldfgjalkdfgjlkfdagjakldfgjaldkfgjadflkgjaelkgjlkrjgealkrgjelkargjkealrgjeaklrgdfg', 'password': 'doe'}
            http_helpers.http_req("https://localhost:8080", "POST", "/register", request_body)
        self.assert_400(test)

    def test_login(self):
        request_body = {'username': 'frank', 'password': 'pass'}
        http_helpers.http_req("https://localhost:8080", "POST", "/register", request_body)

        response = http_helpers.http_req("https://localhost:8080", "POST", "/login", json.dumps(request_body))
        session_id = json.loads(response)['session_id']

    def test_login_nonexistent(self):
        request_body = {'username': 'alan', 'password': 'pass'}
        def test(): http_helpers.http_req("https://localhost:8080", "POST", "/login", json.dumps(request_body))
        self.assert_400(test)

    def test_login_wrong_pass(self):
        request_body = {'username': 'joseph', 'password': 'pass'}
        http_helpers.http_req("https://localhost:8080", "POST", "/register", request_body)
        request_body['password'] = 'wrong pass'

        def test(): http_helpers.http_req("https://localhost:8080", "POST", "/login", json.dumps(request_body))
        self.assert_400(test)

    @classmethod
    def tearDownClass(cls):
        cls.p.terminate()
        # Wait for process to terminate
        cls.p.wait()
        os.remove("../unit_test_db.db")