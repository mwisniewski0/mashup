import bcrypt
import pbkdf2
import random
import crypto_helpers
import json
from response import Response
from exceptions import *
import globals


# privileges format:
# user.privilege\n
# user.privilege\n
# user.privilege\n
# ...


class User:
    def __init__(self, username, privileges, password_derived_key, db):
        self.db = db
        self.pd_key = password_derived_key
        self.username = username
        self.privileges = [{"user": record.split('.')[0], "privilege": record.split('.')[1]}
                           for record in privileges.split('\n') if record != ''] if isinstance(privileges, str) else privileges

    def check_privilege(self, user, privilege):
        return {"user":user, "privilege":privilege} in self.privileges

    def grant_privilege(self, user, privilege):
        if not self.check_privilege(user, privilege):
            self.privileges.append({"user":user, "privilege":privilege})
        self.save_to_db()

    def revoke_privilege(self, user, privilege):
        if self.check_privilege(user, privilege):
            self.privileges.remove({"user":user, "privilege":privilege})
        self.save_to_db()

    @staticmethod
    def privilege_to_string(privileges):
        result = ""
        for privilege in privileges:
            result += privilege["user"] + "." + privilege["privilege"] + "\n"
        return result

    def get_privilege_string(self):
        return User.get_privilege_string(self.privileges)

    def save_to_db(self):
        c = self.db.cursor()
        c.execute("UPDATE users SET privilege=? WHERE username=?", (self.get_privilege_string(), self.username))
        c.close()
        self.db.commit()

    def encrypt_with_pd_key(self, data):
        return crypto_helpers.aes_encrypt(data, self.pd_key)

    def decrypt_with_pd_key(self, data):
        return crypto_helpers.aes_decrypt(data, self.pd_key)

class Session:
    def __init__(self, user, session_id):
        self.id = session_id
        self.user = user

    def encrypt(self, data):
        return self.user.encrypt_with_pd_key(data)

    def decrypt(self, data):
        return self.user.decrypt_with_pd_key(data)

class Authenticator:
    def __init__(self, db):
        self.db = db
        self.active_sessions = {}

        c = self.db.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, salt_pass BLOB, hash BLOB, privilege TEXT, salt_encrypt TEXT, PRIMARY KEY(username))")
        c.close()
        self.db.commit()

    def session_encrypt(self, session_id, plaintext):
        return self.active_sessions[session_id].encrypt(plaintext)

    def session_decrypt(self, session_id, cyphertext):
        return self.active_sessions[session_id].decrypt(cyphertext)

    def derive_username_from_session_id(self, session_id):
        return self.active_sessions[session_id].user.username

    def create_session(self, user):
        new_session_id = crypto_helpers.generate_token(self.active_sessions, 64)
        session = Session(user, new_session_id)
        self.active_sessions[new_session_id] = session

        return session

    def get_reserved_usernames(self):
        return ['all']

    def get_min_username_length(self):
        return 3

    def get_max_username_length(self):
        return 64

    def get_valid_username_chars(self):
        return "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_"

    def add_user(self, username, password, privileges):
        # validate username
        if (username in self.get_reserved_usernames()):
            raise MashupAccessException("Username is not available",
                                          "User tried to take a reserved username: " + username)
        if (len(username) < self.get_min_username_length()):
            raise MashupAccessException("Username needs to be at least " + self.get_min_username_length()
                                        + " characters long", "")
        if (len(username) > self.get_max_username_length()):
            raise MashupAccessException("Username needs to be at most " + self.get_max_username_length()
                                        + " characters long", "")
        for char in username:
            if char not in self.get_valid_username_chars():
                raise MashupAccessException("Username can only contain alpha-numeric characters and the underscore", "")

        c = self.db.cursor()
        c.execute("SELECT username FROM users WHERE username=?", (username,))
        c.close()
        self.db.commit()
        if c.rowcount > 0:
            raise MashupAccessException("Username is not available",
                                  "User tried to take a username that has already been taken: " + username)
        # username is valid

        salt = bcrypt.gensalt()
        hash = bcrypt.hashpw(password.encode('utf-8'), salt)

        c = self.db.cursor()
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                  (username, salt, hash, User.privilege_to_string(privileges), bcrypt.gensalt()))
        c.close()
        self.db.commit()

    def authorize(self, session_id, user, privilege):
        if session_id not in self.active_sessions:
            raise MashupAccessException("Provided session_id is not valid")

        session = self.active_sessions[session_id]
        if not session.user.check_privilege(user, privilege):
            raise MashupAccessException("Access forbidden")

    def accept_login_connection(self, method, body):
        if method != 'post':
            raise MashupBadRequestException("Login requests need to be executed through POST")
        else:
            login = ""
            password = ""
            try:
                params = json.loads(body)
                login = params['username']
                password = params['password']
            except Exception:
                raise MashupBadRequestException("The request body does not contain a valid login request")
            session = self.authenticate(login, password)
            globals.get_resource("modules").clouds_manager.load_session(session.id)
            return Response.from_json({'session_id': session.id})

    def authenticate(self, username, password):
        c = self.db.cursor()
        c.execute("SELECT salt_pass, hash, privilege, salt_encrypt FROM users WHERE username=?", (username,))

        results = c.fetchall()
        c.close()
        self.db.commit()
        if len(results) == 0:
            raise MashupAccessException("Authentication failed", "No user with that username: " + username)

        # since username is unique there will be just one result
        user_row = results[0]
        hashFromProvidedPass = bcrypt.hashpw(password.encode('utf-8'), user_row[0])

        if hashFromProvidedPass == user_row[1]:
            # make a 32 bits AES key
            password_derived_key = pbkdf2.PBKDF2(password, user_row[3]).read(32)
            user = User(username, user_row[2], password_derived_key, self.db)
            session = self.create_session(user)
            return session
        else:
            raise MashupAccessException("Authentication failed", "Passwords do not match for user: " + username)

    def is_valid_session(self, session_id):
        return session_id in self.active_sessions