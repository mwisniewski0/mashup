import http.client, urllib.parse


def start_connection(address):
    protocol = address.split(':')[0].lower()
    address = address[len(protocol)+3:]

    if protocol == 'http':
        return http.client.HTTPConnection(address)
    elif protocol == 'https':
        return http.client.HTTPSConnection(address)
    else:
        raise Exception('Address does not contain the protocol')

def direct_http_req(url_string, method, body=None, headers={}, return_full_response=False):
    protocol = url_string.split(':')[0].lower()
    url_string = url_string[len(protocol) + 3:]
    index_of_first_slash = url_string.index('/') + len(protocol) + 3
    address = url_string[:index_of_first_slash]
    path = url_string[index_of_first_slash:]
    return http_req(address, method, path, body, {}, headers, return_full_response)

def http_req(connection, method, path = "", body = None, query_values = {}, headers = {}, return_full_response = False):
    close_connection = False
    if isinstance(connection, str):
        close_connection = True
        connection = start_connection(connection)

    if isinstance(body, dict):
        if 'content-type' not in [key.lower() for key in headers.keys()]:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        body = urllib.parse.urlencode(body)

    query_string = urllib.parse.urlencode(query_values)
    if query_string != '':
        query_string = '?' + query_string
    connection.request(method.upper(), path + query_string, body, headers)
    response = connection.getresponse()
    data = response.read()

    if close_connection:
        connection.close()

    if return_full_response:
        return data, response
    else:
        if response.status < 300:
            return data.decode('utf-8')
        else:
            raise Exception("HTTP call failed: " + response.reason, data.decode('utf-8'))

def auth_http_req(connection, session_id, method, path, body = None, query_values = {}, headers = {}):
    headers['X_SESSION_ID'] = session_id
    return http_req(connection, method, path, body, query_values, headers)