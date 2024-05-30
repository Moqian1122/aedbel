# AEDBel: A quick AED-searching application designed by Group Italy, KU Leuven for Modern Data Analytics

**Why Heroku?**

- Free for hobby apps, great to get started and for demos;
- Clear, concise documentation;
- Natively supports Python web apps.

**Heroku Command Line Interface (CLI)**

The Heroku CLI is an essential part of using Heroku. With it, you can create and manage Heroku apps directly from the terminal.

**Explanation**

To deploy an app using dash to server with Heroku, the following documents are necessary:

(1) Procfile
content: normally we just use 'web: gunicorn app:server' as a text in the file to tell Heroku to use web application and HTTP server. 
function: to specify the task and objects to execute to Heroku
note: 'gunicorn' requires to be installed and loaded via 'requirements.txt' as well.

(2) app.py
content: the python code file
function: to run the main programme

(3) runtime.txt
content: I used 'python-3.12.3'
function: to specify the python version to use

(4) requirements.txt
content: dependencies

**Issue fixed**

Database importer - for files of small size like a signle csv or xlsx file, make sure the file is put in the same directory in the root folder;

**Maintainance**

In the end, we could go back to creator account to maintain the status of the application.

![image](https://github.com/Moqian1122/aedbel/assets/162614386/66fac628-8fdd-48b6-9305-82f374e2c0d7)
