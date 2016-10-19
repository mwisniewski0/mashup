# mashup
Cloud Storage layer of abstraction providing a single file system for different cloud accounts.

To install the service, you need to install
pip3 install bcrypt
pip3 install pbkdf2
pip3 install dropbox

Dummy acounts:
One drive: john_doe_cp341@outlook.com
           Placeholder
Dropbox: john_doe_cp341@outlook.com
         Placeholder

To run the server:
python3 program.py gunicorn -sqlfile "mashup_sql.db" -certfile server.crt -keyfile server.key

To run the client:
python3 client.py