# AEDBel: A quick AED-searching application

<img src="AED_Bel.png" alt="APP icon" width="100" height="100">

## Introduction

AEDBel is an application developed, deployed and operated by Group Italy from KU Leuven for the course Modern Data Analytics. The application is designed for saving rescuers more valuable time whenever a cardiac arrest happen. Based on optimized AED locations, AEDBel requests users' location to calculate the nearest AED in a short time. It provides walking/driving mode in terms of suggesting routes. It also displays points of interest and estimated time of arrival considering the rushy scenario. Besides, some tutorial videos about AED operation and CPR could be found in the APP.

## Members ##
AEDBel is deveopled, deployed and operated by Group Italy. Group Italy has four members.

Massimo Gerecitano

Moqian Chen

Jorge Puertolas Molina

Shyam Krishna Selvan


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
