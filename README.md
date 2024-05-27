Heroku:

The GitHub space is a repository linked to Heroku.

To deploy an app using dash to server with Heroku, the following documents are necessary:

(1) Procfile
content: normally we just use 'web: gunicorn app:server' as a text in the file to tell Heroku to use web application and HTTP server. 
function: to specify the task and objects to execute to Heroku

(2) app.py
content: the python code file
function: to run the main programme

(3) runtime.txt

