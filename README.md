# SNOW BEAR GENERATOR

A simple python script to send an email with an image 
of a certain white bear in the style of a famous artwork or poster.
An llm was used to generate a starter list of 100 artworks to use as style references,
which are stored in the artworks array in icebear.py. The array is indexed
as the number of days since a target date, which is currently April 29, 2025. 

It will loop after 100 days, and start again from the first artwork. If you wish 
to add more artworks to the list, you can do so by adding them to the artworks array,
and if you wish to change the current 'index', you can change the target_date variable.


# ENVIRONMENT VARIABLES
The script uses the openai API to generate the image, and the Mailgun API to send the email.

The following environment variables are required:
- OPENAI_API_KEY
- MAILGUN_API_KEY
- MAILGUN_DOMAIN
- MAILGUN_FROM
- MAILGUN_TO
- MAILGUN_TO_NAME
- MAILGUN_CC_EMAILS (optional) - a comma separated list of email addresses to cc the email to
- GOOGLE_SEARCH_API_KEY (for the google custom search API, icebear-selfgen-image.py)
- GOOGLE_SEARCH_ENGINE_ID (for the google custom search API, icebear-selfgen-image.py)

# RUNNING LOCALLY

to run the script locally, you can use the following command:
first create a virtual environment and install the requirements:
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
then run the script:    
```
python icebear.py
```

# RUNNING AS A CRON JOB 

here is a bash command for running the script:

```
#!/bin/bash

# Go to the project directory (replace with your absolute path)
cd ~/github/snowbearGenerator

# Activate virtual environment
source .venv/bin/activate

# Run the script
python icebear.py

# Deactivate virtual environment
deactivate
``` 

then add the following to your crontab:
```
0 9 * * * PATHTO/run_icebear.sh >> PATHTO/snowbearGenerator/icebear.log 2>&1
```


