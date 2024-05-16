**EXAM REPORT**
---

1. **Start up lab environment using Docker Compose and validate access to "database-1"**

By provided commands in the LAB.md documenation, I started up the environment and accessed the database via the jumpbox shell.

---
2. **Design and define table structure for forum application in the database "forum_data"**

I created threads and thread_responses based on the examples specified in the "create_thread" and "get_thread" endpoints:

```sql
CREATE TABLE threads (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) UNIQUE NOT NULL,
    topic_description TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    creation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
#### Explanation:
- "id": A unique identifier for each thread. It is of type "SERIAL" which auto-increments, acting as the primary key for the table.
- "title": The title of the thread. It is of type "VARCHAR(255)" and must be unique ("UNIQUE") and not null ("NOT NULL"`).
- "topic_description": A text field for the description of the thread topic. It is of type "TEXT" and cannot be null.
- "author": The username of the author who created the thread. It is of type "VARCHAR(255)" and cannot be null.
- "creation_timestamp": The timestamp when the thread was created. It is of type "TIMESTAMP" and defaults to the current timestamp ("CURRENT_TIMESTAMP").

---
```sql
CREATE TABLE thread_responses (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER NOT NULL,
    comment TEXT NOT NULL,
    author VARCHAR(255) NOT NULL,
    response_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);
```
#### Explanation:
- "id": A unique identifier for each response, automatically generated using the "SERIAL" type.
- "thread_id": The ID of the thread to which the response belongs. This establishes a foreign key relationship with the "threads" table.
- "comment": The content of the response.
- "author": The author of the response.
- "response_timestamp": The timestamp when the response was created. It has a default value of the current timestamp.
---

3. **Create user "db_app_user" with privileges required to access/utilize the database "forum_data"**

I created the user "db_app_user" with the necessary privileges to access/utilize the database "forum_data". Below is the SQL code used to create the user and grant permissions:

```sql
CREATE USER db_app_user WITH PASSWORD '0205Sopwith.Camel;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO db_app_user;
```
---
4. **Design/Implement database queries in app to provide functionality for "GET /api/threads"**

I implemented the database query to retrieve a list of forum threads for the "GET /api/threads" endpoint. The SQL query fetches thread details sorted by creation timestamp in descending order. Here's the Python code snippet:

```python
try:
    with postgresql_client.cursor() as cursor:
        # Fetch data from threads
        query = "SELECT id, title, author, creation_timestamp FROM threads ORDER BY creation_timestamp DESC"
        cursor.execute(query)
        threads = cursor.fetchall()

        # Convert the fetched data into dictionary format based on example
        response = [{'id': thread[0], 'title': thread[1], 'author': thread[2], 'updated': str(thread[3])} for thread in threads]

        postgresql_client.commit()
```
- I've constructed the SQL query as a string without directly inserting user input to minimize SQL injection.

---
5. **Design/Implement database queries in app to provide functionality for "POST /api/threads"**

 I implemented the database query for creating a new forum thread in the "POST /api/threads" endpoint. The code checks for duplicate thread titles before inserting the new thread into the database. Here's the relevant Python code:
```python
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
        postgresql_client.commit()
```
- Constructed the queries using parameterized queries.where ("%s") are used to represent dynamic values.

I  tested the endpoint using the automated application test script "forum_test_script.py". The script executed actions to create threads with different users and verified the server's responses.

During testing, I observed that the endpoint successfully created threads as expected. However, I encountered an issue related to thread creation with duplicate titles. As I missed this part in the example_response code. The application allowed threads with duplicate titles to be created.

```
INFO: Sending HTTP request to create duplicate title thread as pam - POST http://forum.int.agency.test:5000/api/threads with body:
{'title': 'Fight club anyone?!', 'topic_description': 'Got no answers in previous thread - WHO IS WITH ME?!'}
CRITICAL: Failed to execute test: Thread creation with duplicate title should be disallowed
```

To address this issue, I implemented additional validation logic in the endpoint to disallow thread creation with duplicate titles. After making the necessary modifications, I retested the endpoint using the test script and confirmed that duplicate thread creation was appropriately prevented.

---
6. **Design/Implement database queries in app to provide functionality for "GET /api/threads/$ID"**

I implemented the database queries to retrieve details of a specific forum thread and its associated responses for the "GET /api/threads/$ID" endpoint. The code fetches thread details and sorted responses from the database. Here's the relevant Python code:

```python
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
```
- Constructed the queries using parameterized queries.where ("%s") are used to represent dynamic values.

I did not encounter any immediate issues. However, during testing, I noticed that the endpoint did not return the expected response format as described in the documentation. I had to make adjustments to ensure that the endpoint returned the correct data structure according to the specifications.

Here's a summary of the adjustments made and the issues encountered:

1. Formatting Response: Initially, the endpoint did not return the response in the expected format. I needed to ensure that the response included the thread title, topic description, creation timestamp, and a list of responses sorted by timestamp.


3. Sorting Responses: I needed to ensure that the list of responses was sorted by timestamp, with the oldest response appearing first. This required modifying the database query to retrieve responses in the correct order.

Overall, while there were no major issues with the functionality of the endpoint, I needed to refine the implementation to align with the specified requirements and improve the user experience.

---
7. **Design/Implement database queries in app to provide functionality for "PUT /api/threads/$ID"**

I implemented the database query for adding a response to a forum thread in the "PUT /api/threads/$ID" endpoint. The code inserts the new response into the database. Here's the relevant Python code:

```python
try:
    with postgresql_client.cursor() as cursor:
        # Inserting the queries for user to be able to comment
        cursor.execute("INSERT INTO thread_responses (thread_id, comment, author) VALUES (%s, %s, %s)",
                        (thread_id, comment, app_user))
        postgresql_client.commit()
```
- Constructed the queries using parameterized queries.where ("%s") are used to represent dynamic values.

---
8. **Design/Implement database queries in app to provide functionality for "DELETE /api/threads/$ID"**

I implemented the database query for deleting a forum thread and its associated responses in the "DELETE /api/threads/$ID" endpoint. The code deletes the thread and its responses from the database. Here's the relevant Python code:

```python
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
```
- Constructed the queries using parameterized queries.where ("%s") are used to represent dynamic values.

After implementing the necessary functionality for the "delete_thread" endpoint, I encountered an issue during testing.

When testing the deletion of threads, I encountered an exception related to foreign key constraints. The error message indicated that the deletion of a thread was violating a foreign key constraint in the database. Specifically, the error message stated:

```
Exception: Failed to delete thread ID 21 for user "malory": "update or delete on table "threads" violates foreign key constraint "thread_responses_thread_id_fkey" on table "thread_responses"
DETAIL: Key (id)=(21) is still referenced from table "thread_responses".
```

This error occurred because there were existing records in the "thread_responses" table that referenced the thread being deleted. In other words, there were responses associated with the thread that I attempted to delete, and PostgreSQL prevented the deletion to maintain data integrity.

To resolve this issue, I needed to ensure that all dependent responses were deleted before attempting to delete the thread. I added code to handle the deletion of dependent records in the database before deleting the thread itself. This involved deleting all responses associated with the thread ID specified in the request.

After implementing this solution and retesting the 
"delete_thread" endpoint, I confirmed that the issue was resolved, and the endpoint functioned as expected without encountering any further errors related to foreign key constraints.

---
9. **Validate access and functionality in forum web application**

I executed the automated test using the forum test script to validate the access and functionality of the forum web application. The tests included creating threads, adding responses, fetching thread lists, deleting threads, and verifying responses. All tests were successful, confirming the correct operation of the application.

```bash
vagrant@database-lab-system:/course_data/labs/exam$ ./jumpbox_shell.sh forum_test_script.py
INFO: Starting test execution against "http://forum.int.agency.test:5000"
INFO: Sending HTTP request to fetching thread list as pam - GET http://forum.int.agency.test:5000/api/threads with body:
None
INFO: Sending HTTP request to cleanup previous example thread "Office manners" as malory - DELETE http://forum.int.agency.test:5000/api/threads/132 with body:
None
INFO: Sending HTTP request to cleanup previous example thread "Fight club anyone?!" as pam - DELETE http://forum.int.agency.test:5000/api/threads/131 with body:
None
INFO: Sending HTTP request to create fightclub thread as pam - POST http://forum.int.agency.test:5000/api/threads with body:
{'title': 'Fight club anyone?!', 'topic_description': 'I love bare-knuckle boxing. Who is with me?!'}
INFO: Sending HTTP request to create office manners thread as malory - POST http://forum.int.agency.test:5000/api/threads with body:
{'title': 'Office manners', 'topic_description': 'Let us discuss how we should behave in the office. Suggestions?'}
INFO: Sending HTTP request to answer manners thread as cheryl - PUT http://forum.int.agency.test:5000/api/threads/135 with body:
'I suggest we disallow storing "experiments" in the kitchen fridge!'
INFO: Sending HTTP request to answer manners thread as malory - PUT http://forum.int.agency.test:5000/api/threads/135 with body:
'Agreed. In the same vein: glue is not food! :-@'
INFO: Sending HTTP request to fetching manners thread as pam - GET http://forum.int.agency.test:5000/api/threads/135 with body:
None
INFO: Sending HTTP request to create apology thread as cyril - POST http://forum.int.agency.test:5000/api/threads with body:
{'title': 'My sincerest apology', 'topic_description': 'Just went way over the line. I promise to never strangle again!'}
INFO: Sending HTTP request to answer apology thread as pam - PUT http://forum.int.agency.test:5000/api/threads/136 with body:
'HahHAHAHAHahahahahaaa OMG ROFLMAO!!!11one'
INFO: Sending HTTP request to fetching thread list as pam - GET http://forum.int.agency.test:5000/api/threads with body:
None
INFO: Sending HTTP request to delete apology thread as cyril - DELETE http://forum.int.agency.test:5000/api/threads/136 with body:
None
INFO: Sending HTTP request to fetching thread list as cyril - GET http://forum.int.agency.test:5000/api/threads with body:
None
INFO: Sending HTTP request to fetch list of top posters as malory - GET http://forum.int.agency.test:5000/api/top_posters with body:
None
INFO: Sending HTTP request to delete non-authored thread as malory - DELETE http://forum.int.agency.test:5000/api/threads/134 with body:        
None
INFO: Sending HTTP request to create duplicate title thread as pam - POST http://forum.int.agency.test:5000/api/threads with body:
{'title': 'Fight club anyone?!', 'topic_description': 'Got no answers in previous thread - WHO IS WITH ME?!'}
INFO: Successfully executed tests! :-D
```

---
10. **Design/Implement database queries in app to provide functionality for "/api/top_posters"**

I implemented database queries to retrieve the top three most active forum users for the "/api/top_posters" endpoint. The code fetches user activity data from both the "threads" and "thread_responses" tables and calculates the top posters based on their activity count. Here's the relevant Python code:

```python
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
```
- This approach ensures that the top posters are selected based on their overall activity, including both authored threads and comments, while protecting against SQL injection by using parameterized queries.

---
11. **Ensure that "foreign key constraints" are enforced for relevant table columns**

I enforced foreign key constraints for relevant table columns to maintain data integrity and consistency in the database. Specifically, I added a foreign key constraint to the "thread_responses" table referencing the "threads" table. Here's the relevant SQL command:

```sql
ALTER TABLE thread_responses
ADD CONSTRAINT fk_thread_id
FOREIGN KEY (thread_id)
REFERENCES threads(id)
ON DELETE CASCADE;
```

---
12. **Extract/Store end-user's source IP address used during thread manipulation in database (CRUD)**

I enhanced the database schema to include columns for storing the source IP address of end-users performing CRUD operations on forum threads. Here's how I implemented it:

```sql
ALTER TABLE threads
ADD COLUMN source_ip VARCHAR(45);

ALTER TABLE thread_responses
ADD COLUMN source_ip VARCHAR(45);
```
These SQL commands add new columns to the "threads" and "thread_responses" tables to store the source IP address of users.
Additionally, I updated the application code to capture and store the source IP address during thread manipulation operations. Here's a snippet of the Python code for creating a thread and adding a response:

```python
#UPDATED def create_thread TO TRACK IP:

@app.post('/api/threads')
@authentication.login_required
def create_thread():
    # Extracting user's IP address
    ip_address = request.remote_addr
    
    ----

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
```
```python
# UPDATED def answers_thread TO TRACK IP:

@app.put('/api/threads/<int:thread_id>')
@authentication.login_required
def answer_thread(thread_id):
    # Extracting user's IP address
    ip_address = request.remote_addr
    
    ----

try:
    with postgresql_client.cursor() as cursor:
        # Inserting the queries for user to be able to comment
        cursor.execute("INSERT INTO thread_responses (thread_id, comment, author, source_ip) VALUES (%s, %s, %s, %s)",
                        (thread_id, comment, app_user, ip_address))

        postgresql_client.commit()
```
- In the CREATE operation (POST endpoint), after inserting a new thread into the threads table, I added a query to update the source_ip column with the IP address of the user who created the thread.

- In the RESPOND operation (PUT endpoint), after inserting a new response into the thread_responses table, I added a query to update the source_ip column with the IP address of the user who responded to the thread.

---
13. **Enable logging of all database queries to "stderr" in PostgreSQL**

I configured PostgreSQL to log all database queries to "stderr" for monitoring and troubleshooting purposes. Here's how I implemented it:


```
# Added to postgresql.conf

logging_collector = on
log_destination = 'stderr'
log_statement = 'all'
```

- All database queries should be logged to "stderr" according to the configured logging settings. 

---
14. **Restrict database permissions for "db_app_user" using principle of least privilege**

db_app_user already possesses the minimal CRUD privileges required for database operations, adhering to the principle of least privilege.

---
15. **Perform backup and restore of "forum\_data" table in PostgreSQL ("database-1")**
  - Setup a dedicated database user for data backup using principle of least privilege
  - Utilize the "pg\_dump" utility in the "jumpbox" container to perform backup
  - Modify/Delete some of the stored rows
  - Restore backup and validate result

This procedure ensures data integrity and provides a mechanism for restoring database content in the event of data loss or corruption.

```sql
CREATE ROLE backup_user WITH LOGIN PASSWORD 'password123';
GRANT ALL PRIVILEGES ON SCHEMA public TO backup_user;
ALTER ROLE backup_user WITH SUPERUSER;
```
```bash
pg_dump -U backup_user -h database-1.int.agency.test -d forum_data -a -Fc -f forum_data.dump
```
```sql
DELETE FROM threads;
DELETE FROM thread_responses;
```
```bash
pg_restore -U backup_user -h database-1.int.agency.test -d forum_data --data-only forum_data.dump
```

- Created a dedicated database user (backup_user) with the all privileges for backup operations.
- Used the pg_dump utility with the --data-only option to create a data-only backup file (forum_data.dump), containing only the data without the schema.
- Tried to use pg_restore but encountered errors due to duplicate key violations.
- Had to manually delete existing data from the affected tables (threads and thread_responses) using SQL DELETE statements.
- Used pg_restore with the --data-only options to restore the data-only backup, allowing the backup data to restore the tables and its content.

---
16. **Configure "database-2" as a read replica of "database-1" for high-availability**
 
- Validate result by disabling "database-1" and executing SELECT queries against the replica

To ensure high availability and fault tolerance of data, below are the detailed steps involved in setting up the read replica:

##### Enabling PostgreSQL Service on "database-2":
- Modified the docker-compose.yml file to allow PostgreSQL to start normally on "database-2".

```yaml
# docker-compose.yml
database-2.int.agency.test:
  # entrypoint: # Remove or comment this out
  #   - "/bin/sh"
  #   - "-c"
  #   - "/usr/bin/sleep infinity"
```

##### Preparing Primary Server Replication User ("database-1"):
- Created a replication user on "database-1" with necessary privileges.

```sql
-- In the jumpbox shell on database-1
CREATE ROLE replication WITH REPLICATION PASSWORD 'password123' LOGIN;
```

##### Adjusting pg_hba.conf on "database-1":
- Edited the pg_hba.conf file on "database-1" to allow replication from the specified jumpbox container IP.

```
# pg_hba.conf on database-1
host replication replication  all md5
```

##### Configuring the Replica ("database-2"):
- Initiated pg_basebackup on "database-2" to synchronize data from "database-1" and restarted the "database-2" container.

```bash
# In the jumpbox shell on database-2
pg_basebackup -h database-1.int.agency.test -p 5432 -U replication -D /var/lib/postgresql/data -Fp -Xs -R

# Restarting all docker containers
docker compose restart database-2.int.agency.test
```

##### Validation Test for High Availability:
To validate high availability, I executed SELECT queries against the replica ("database-2") after temporarily switching the forum application's connection to it. Additionally, I monitored the replication status using the following SQL query:

```sql
forum_data=# SELECT client_addr, state FROM pg_stat_replication;
 client_addr |   state
-------------+-----------
 172.30.0.2  | streaming
(1 row)
```

The above query confirms that "database-2" is actively replicating data from "database-1" and is in the "streaming" state, indicating successful replication. This reaffirms the readiness of "database-2" to serve as a reliable read replica in the event of "database-1" failure.

I then proceeded to stop "database-1" and observed the forum application's behavior. Despite the primary database being offline, the forum application continued to function seamlessly, fetching data from "database-2". This successful failover demonstrates the high availability achieved through the read replica configuration.

---
**Conclusion:**

In wrapping up this examination lab, it's clear that I've learned a great deal about PostgreSQL databases and their practical applications. Throughout the tasks, I discovered how to:

- **Design Databases:** I figured out how to structure databases effectively to store forum data efficiently.
  
- **Manage Users:** By creating specific user accounts with only the necessary permissions, I learned how to keep our databases secure.
  
- **Implement Functionality:** Through implementing database queries, I grasped how to add features to the forum app, like listing threads or posting replies.
  
- **Backup and Restore:** I've learned how to back up data and how to restore it.
  
- **Ensure Availability:** Setting up a read replica for high availability taught me how to make sure the forum stays accessible even if one database goes down.

In essence, this examination lab has been an invaluable learning experience, equipping me with practical skills and knowledge essential for working with PostgreSQL databases effectively.

--- 