# SPDX-FileCopyrightText: © 2024 Menacit AB <foss@menacit.se>
# SPDX-License-Identifier: CC-BY-SA-4.0
# X-Context: Database course - Examination lab - Source code for "forum" web application

'''
forum - Web application for meaningful and productivity-boosting discussions.
'''

try:
    import logging as _log
    import time
    
    from flask import Flask, request, jsonify
    from flask_httpauth import HTTPBasicAuth
    from psycopg import connect as postgresql
    import yaml
    
except Exception as error_message:
    raise Exception(f'Failed to import required Python dependencies: {error_message}')

# -------------------------------------------------------------------------------------------------
# Load configuration from YAML file and validate that required keys/options are present
configuration_path = '/etc/app_configuration.yml'

try:
    with open(configuration_path, 'r') as file_handle:
        raw_configuration = yaml.safe_load(file_handle)
        
except Exception as error_message:
    raise Exception(f'Failed to load configuration from "{configuration_path}": {error_message}')

if not isinstance(raw_configuration, dict):
    raise Exception(f'The file "{configuration_path}" is not parsable as a dictionary')

for required_key in ['log_level', 'app_users', 'database_settings']:
    if not required_key in raw_configuration.keys():
        raise Exception(f'Missing option/key "{required_key}": ' + repr(raw_configuration))  
    
if not isinstance(raw_configuration['app_users'], dict):
    raise Exception('Option "app_users" must be a dictionary (key=username, value=password)')

if not isinstance(raw_configuration['database_settings'], dict):
    raise Exception(f'Option "database_settings" must be parseable as a dictionary')
    
for required_key in ['remote_hosts', 'user', 'password', 'database_name']:
    if not required_key in raw_configuration['database_settings'].keys():
        raise Exception(
            f'Missing "database_settings" option/key "{required_key}": ' + repr(raw_configuration))

if not isinstance(raw_configuration['database_settings']['remote_hosts'], list):
    raise Exception(
        f'"remote_hosts" option in "database_settings" must be a list: ' + repr(raw_configuration))

match raw_configuration['log_level']:
    case 'INFO':
        logger_level = _log.INFO

    case 'DEBUG':
        logger_level = _log.DEBUG
        
    case _:
        raise Exception('Option "log_level" is invalid (must be "INFO" or "DEBUG")')

_log.basicConfig(format='%(levelname)s: %(message)s', level=logger_level)
_log.debug('Loaded app configuration: ' + repr(raw_configuration))

app_users = raw_configuration['app_users']
database_settings = raw_configuration['database_settings']

# -------------------------------------------------------------------------------------------------
_log.info('Initializing PostgreSQL client with specified settings')

postgresql_hosts = ','.join(database_settings['remote_hosts'])
s = database_settings
target_uri = f'postgresql://{s['user']}:{s['password']}@{postgresql_hosts}/{s['database_name']}'
_log.debug(f'PostgreSQL connection URI: {target_uri}')

try:
    postgresql_client = postgresql(target_uri)
    _log.debug('Connected to database: ' + postgresql_client.info.dsn)
    
except Exception as error_message:
    raise Exception(f'Failed to connect to PostgreSQL database: "{error_message}"')

# -------------------------------------------------------------------------------------------------
_log.debug('Setting up Flask application and authentication extension')

app = Flask('forum')
authentication = HTTPBasicAuth()


# -------------------------------------------------------------------------------------------------
@authentication.verify_password
def verify_credentials(app_user, password):
    _log.info(f'Checking login credentials for app user "{app_user}"')
    _log.debug(f'Password associated with app user "{app_user}" in login attempt: {password}')

    if not app_user in app_users.keys():
        _log.warning(f'Non-existing app user "{app_user}" tried to authenticate')
        return

    if not password == app_users[app_user]:
        _log.warning(f'App user "{app_user}" tried to authenticate with invalid password')
        return

    _log.debug(f'Successfully authenticated app user "{app_user}"')
    return app_user


# -------------------------------------------------------------------------------------------------
@app.route('/is_the_server_up_and_running', methods=['GET', 'HEAD'])
def return_health_status():
    return f'Yes, the web application does indeed seem to be up and running!'


# -------------------------------------------------------------------------------------------------
@app.get('/api/threads')
@authentication.login_required
def list_threads():
    
    '''
    Purpose: Return list of threads.
    Expected response: List of threads with ID, title, author and last update timestamp.
    Sorting: Latest updated threads first.
    Constraints: None
    Request body structure: None
    '''
    """
    example_response = [
        {
            'id': 2,
            'title': 'Office manners',
            'author': 'malory',
            'updated': '2024-03-03 10:23:52+01'
        },
        {
            'id': 1,
            'title': 'Fight club anyone?!',
            'author': 'pam',
            'updated': '2024-03-01 14:39:42+01'
        }
    ]
    """
    # ---------------------------------------------------------------------------------------------
    app_user = authentication.current_user()
    _log.info(f'Fetching list of threads for user "{app_user}"')
    
    response = []
    try:
        with postgresql_client.cursor() as cursor:
            # Fetch data from threads
            query = "SELECT id, title, author, creation_timestamp FROM threads ORDER BY creation_timestamp DESC"
            cursor.execute(query)
            threads = cursor.fetchall()

            # Convert the fetched data into dictionary format
            response = [{'id': thread[0], 'title': thread[1], 'author': thread[2], 'updated': str(thread[3])} for thread in threads]

            postgresql_client.commit()
    
    except Exception as error_message:
        postgresql_client.rollback()
        raise Exception(
            f'Failed fetching thread list for user "{app_user}" from database: "{error_message}"')

    _log.debug('Generated response data for thread listing: ' + repr(response))

    return jsonify(response)


# -------------------------------------------------------------------------------------------------
@app.post('/api/threads')
@authentication.login_required
def create_thread():
    # Extracting user's IP address
    ip_address = request.remote_addr
    '''
    Purpose: Create forum thread.
    Expected response: Thread ID
    Sorting: None
    Constraints:
        - Thread title must be unique
        - Authoring user and creation timestamp should be stored.

    Request body structure:
    
    ```
    {
        'title': 'Office manners',
        'topic_description': 'Let us discuss how we should behave in the office. Suggestions?'
    }
    ```
    '''
    # example_response = 2
    # ---------------------------------------------------------------------------------------------
    app_user = authentication.current_user()
    _log.info(f'Creating new thread for user "{app_user}"')

    _log.debug('Trying to parse request body data as JSON')
    request_data = request.json
    _log.debug('Parsed request data: ' + repr(request_data))

    log_suffix = f' from user "{app_user}": ' + repr(request_data)

    if not isinstance(request_data, dict):
        _log.warning('Could not parse request data as dictionary' + log_suffix)
        return 'Invalid format of request body', 400

    for required_key in ['title', 'topic_description']:
        if not required_key in request_data.keys():
            _log.warning(f'Could not find key "{required_key}" in request data' + log_suffix)
            return 'Missing key in request body', 400
        
        if not isinstance(request_data[required_key], str):
            _log.warning(f'Key "{required_key}" in request data must be a string' + log_suffix)
            return 'Invalid key type in request body', 400

        if not request_data[required_key]:
            _log.warning(f'Key "{required_key}" is an empty string in request data' + log_suffix)
            return 'Invalid value for key in request body', 400

    title = request_data['title']
    topic_description = request_data['topic_description']
    _log.info(f'Creating thread "{title}" for "{app_user}" with description "{topic_description}"')
    
    # --------------------------------------------------------------------------------------------
    try:
        with postgresql_client.cursor() as cursor:
            # Check if the thread with the same title already exists
            cursor.execute("SELECT id FROM threads WHERE title = %s", (title,))
            existing_thread = cursor.fetchone()
            if existing_thread:
                return existing_thread

            # If not, insert the new thread
            cursor.execute("INSERT INTO threads (title, topic_description, author) VALUES (%s, %s, %s) RETURNING id",
                           (title, topic_description, app_user))
            thread_id = cursor.fetchone()[0]

            # Store IP address along with other data
            cursor.execute("UPDATE threads SET source_ip = %s WHERE id = %s", (ip_address, thread_id))

            postgresql_client.commit()
    
    except Exception as error_message:
        postgresql_client.rollback()
        raise Exception(
            f'Failed creating thread for user "{app_user}": "{error_message}"')

    _log.debug('Generated response data for thread creation: ' + repr(thread_id))

    return jsonify(thread_id)


# -------------------------------------------------------------------------------------------------
@app.get('/api/threads/<int:thread_id>')
@authentication.login_required
def get_thread(thread_id):

    '''
    Purpose: Get content from specified forum thread.
    Expected response:
        - Thread title
        - Topic description
        - Topic creation timestamp
        - List of responses with comment, author and response timestamp
    
    Sorting: List of responses sorted by response timestamp (oldest first)
    Constraints: None
    Request body structure: None
    '''
    """
    # Example response format
    example_response = {
        'title': 'Office manners',
        'topic_description': 'Let us discuss how we should behave in the office. Suggestions?',
        'created': '2024-03-02 16:11:40+01',
        'author': 'malory',
        'responses': [
            {
                'comment': 'I suggest we disallow storing "experiments" in the kitchen fridge!',
                'author': 'cheryl',
                'responded': '2024-03-03 03:28:10+01'
            },
            {
                'comment': 'Agreed. In the same vein: glue is not food! :-@',
                'author': 'malory',
                'responded': '2024-03-03 10:23:52+01'
            }
        ]
    }
    """

    # ---------------------------------------------------------------------------------------------
    app_user = authentication.current_user()
    _log.info(f'Fetching content of thread ID {thread_id} for user "{app_user}"')

    try:
        with postgresql_client.cursor() as cursor:
            # Fetch threads
            query_thread = """
                SELECT title, topic_description, author, creation_timestamp 
                FROM threads WHERE id = %s
            """
            cursor.execute(query_thread, (thread_id,))
            thread_data = cursor.fetchone()

            # Extract thread details
            thread_title, topic_description, author, created = thread_data

            # Fetch responses for the thread
            query_responses = """
                SELECT comment, author, response_timestamp 
                FROM thread_responses 
                WHERE thread_id = %s 
                ORDER BY response_timestamp ASC
            """
            cursor.execute(query_responses, (thread_id,))
            responses_data = cursor.fetchall()

            # Convert the fetched data into the desired example format
            responses = [{'comment': response[0], 'author': response[1], 'responded': str(response[2])} for response in responses_data]

            # Construct the response object
            response = {
                'title': thread_title,
                'topic_description': topic_description,
                'created': str(created),
                'author': author,
                'responses': responses
            }

            postgresql_client.commit()
    
    except Exception as error_message:
        postgresql_client.rollback()
        raise Exception(f'Failed to fetch thread content for user "{app_user}": "{error_message}"')

    _log.debug('Generated response data for thread content: ' + repr(response))

    return jsonify(response)


# -------------------------------------------------------------------------------------------------
@app.put('/api/threads/<int:thread_id>')
@authentication.login_required
def answer_thread(thread_id):
    # Extracting user's IP address
    ip_address = request.remote_addr

    '''
    Purpose: Respond to specified forum thread.
    Expected response: None
    Sorting: None
    Constraints: Authoring user and response timestamp should be stored.
    Request body structure:

    ```
    'I suggest we disallow storing "experiments" in the kitchen fridge!'
    ```
    '''
    
    # ---------------------------------------------------------------------------------------------
    app_user = authentication.current_user()
    _log.info(f'Responding to thread ID {thread_id} for user "{app_user}"')

    _log.debug('Trying to parse request body data as JSON')
    request_data = request.json
    _log.debug('Parsed request data: ' + repr(request_data))

    log_suffix = f' from user "{app_user}": ' + repr(request_data)

    if not isinstance(request_data, str):
        _log.warning('Could not parse request data as a string' + log_suffix)
        return 'Invalid format of request body', 400

    if not request_data:
        _log.warning('Request body contains an empty string' + log_suffix)
        return 'Invalid value for request body', 400

    comment = request_data
    _log.info(f'Responding to thread ID {thread_id} for "{app_user}" with comment "{comment}"')
    
    # ---------------------------------------------------------------------------------------------
    try:
        with postgresql_client.cursor() as cursor:
            # Inserting the queries for user to be able to comment
            cursor.execute("INSERT INTO thread_responses (thread_id, comment, author, source_ip) VALUES (%s, %s, %s, %s)",
                           (thread_id, comment, app_user, ip_address))

            postgresql_client.commit()
    
    except Exception as error_message:
        postgresql_client.rollback()
        raise Exception(f'Failed to respond to thread for user "{app_user}": "{error_message}"')

    return jsonify('OK')


# -------------------------------------------------------------------------------------------------
@app.delete('/api/threads/<int:thread_id>')
@authentication.login_required
def delete_thread(thread_id):

    '''
    Purpose: Delete specified forum thread.
    Expected response: None
    Sorting: None
    Constraints:
        - Only thread author can delete specified thread.
        - Should result in thread responses also being deleted.
    
    Request body structure: None
    '''

    # ---------------------------------------------------------------------------------------------
    app_user = authentication.current_user()
    _log.info(f'Deleting thread ID {thread_id} for user "{app_user}"')
    
    try:
        with postgresql_client.cursor() as cursor:
            # Check if the thread exists and if the user is authorized to delete it
            cursor.execute("SELECT author FROM threads WHERE id = %s", (thread_id,))
            result = cursor.fetchone()

            thread_author = result[0]

            if thread_author != app_user:
                return thread_author

            # Delete associated responses first
            cursor.execute("DELETE FROM thread_responses WHERE thread_id = %s", (thread_id,))
            
            # Then delete the thread itself
            cursor.execute("DELETE FROM threads WHERE id = %s", (thread_id,))

            postgresql_client.commit()

    except Exception as error_message:
        postgresql_client.rollback()
        raise Exception(
            f'Failed to delete thread ID {thread_id} for user "{app_user}": "{error_message}"')

    return jsonify('OK')


# -------------------------------------------------------------------------------------------------
@app.get('/api/top_posters')
@authentication.login_required
def list_top_posters():

    '''
    Purpose: Return top three most active forum users.
    Expected response: List of (at most) three users.
    Sorting: Most active user first
    Constraints: Should include both authored threads and comments.
    Request body structure: None
    '''
    """
     example_response = [
        'malory',
        'cheryl',
        'pam',
    ]
    """
    try:
        with postgresql_client.cursor() as cursor:
            # Construct SQL query to get the top three most active forum users
            query = """
                SELECT author, COUNT(*) AS activity_count
                FROM (
                    SELECT author FROM threads
                    UNION ALL
                    SELECT author FROM thread_responses
                ) AS combined_activities
                GROUP BY author
                ORDER BY activity_count DESC
                LIMIT 3
            """
            cursor.execute(query)
            top_posters = cursor.fetchall()

            # Extract usernames from the fetched data
            response = [user[0] for user in top_posters]

            postgresql_client.commit()

    except Exception as error_message:
        postgresql_client.rollback()
        raise Exception(f'Failed to fetch top posters: "{error_message}"')

    _log.debug('Generated response data for top forum posters: ' + repr(response))

    return jsonify(response)

# -------------------------------------------------------------------------------------------------
@app.get('/thread/<int:thread_id>')
@authentication.login_required
def get_thread_html(thread_id):
    _log.info(f'Return thread HTML page for user "{authentication.current_user()}" ({thread_id})')
    return app.send_static_file('thread.html')

# -------------------------------------------------------------------------------------------------
@app.get('/')
@authentication.login_required
def get_thread_list_html():
    _log.info(f'Return thread list HTML page for user "{authentication.current_user()}"')
    return app.send_static_file('thread_list.html')
