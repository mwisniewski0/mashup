# Meant to be built with a secure constant server or to be set on startup

standard_constants = {
    'SERVICE_ADDRESS': 'https://localhost:8080',
    'CHUNK_SIZE': 4194304, # 4 MB
    'DEFAULT_QUOTA': 1073741824, # 1 GB
    'DEFAULT_CLOUD_NAME': 'no name'
}

secure_constants = {
    'DROPBOX_PUBLIC': 'j9dbojs5vtvdzdp',
    'DROPBOX_PRIVATE': 'secret',
    'ONEDRIVE_PUBLIC': '9e103bfb-7a74-4d6f-a112-df0dfa2ec6fd',
    'ONEDRIVE_PRIVATE': 'secret'
}


def get_constant(constant_name):
    if constant_name in standard_constants:
        return standard_constants[constant_name]
    elif constant_name in secure_constants:
        return secure_constants[constant_name]
    else:
        raise AttributeError('Constant not found')


resources = {}

def add_resource(resource_name, resource):
    if resource_name in resources:
        raise AttributeError("This resource name is already taken")
    resources[resource_name] = resource

def remove_resource(resource_name):
    del resources[resource_name]

def get_resource(resource_name):
    return resources[resource_name]
