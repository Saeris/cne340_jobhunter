# Drake Costa
# CNE340 Fall 2023
#
# Job Hunter project. Scrapes remotive for job listings and adds them to a MySQL database.
# Adapted from https://github.com/ellisju37073/cne340_jobhunter/blob/master/jobhunter.py
#
# Using docker compose configuration from
# https://stackoverflow.com/questions/75967671/python-mysql-connector-python-how-to-connect-to-docker-container-from-terminal

import mysql.connector
import time
import json
import requests
from datetime import date, datetime, timedelta
import dateutil.parser
import html2text


def connect_to_db():
    conn = mysql.connector.connect(
        user='user',
        password='secret',
        database='cne340', 
        host='127.0.0.1',
        port=3306
    )
    return conn


def create_tables(cursor):
    query = """
        CREATE TABLE IF NOT EXISTS jobs (
            id INT PRIMARY KEY auto_increment,
            job_id varchar(50),
            company varchar (300),
            created_at DATE,
            url TEXT,
            title LONGBLOB,
            description LONGBLOB
        );
    """
    cursor.execute(query)


def add_new_job(cursor, jobdetails):
    job_id = jobdetails['id']
    company = jobdetails['company_name']
    created_at = jobdetails['publication_date'][0:10]
    url = jobdetails['url']
    title = jobdetails['title']
    description = html2text.html2text(jobdetails['description'])
    query = """
        INSERT INTO jobs(job_id, company, created_at, url, title, description)
        VALUES(%s,%s,%s,%s,%s,%s);
    """
    return cursor.execute(query, (job_id, company, created_at, url, title, description))


def check_if_job_exists(cursor, jobdetails):
    query = """
        SELECT id FROM jobs WHERE job_id = %s;
    """
    job_id = jobdetails["id"]
    return cursor.execute(query, (job_id,))


def delete_old_jobs(cursor):
    query = """
        DELETE FROM jobs WHERE created_at < curdate() - interval 14 day;
    """
    return cursor.execute(query)

# TypeScript type of response shape
# type Job {
#   candidate_required_location: string;
#   category: stirng;
#   company_logo: string;
#   company_name: string;
#   description: string;
#   id: number;
#   job_type: string;
#   publication_date: string;
#   salary: string;
#   tags: string[];
#   title: string:
#   url: string;
# }

def jobhunt(cursor):
    # First prune the database of old jobs
    delete_old_jobs(cursor)
    # Fetch jobs from website
    jobpage = json.loads(requests.get("https://remotive.com/api/remote-jobs").text)
    for jobdetails in jobpage['jobs']:
        # First check if the job listing is older than 14 days, skip if true
        created_at = dateutil.parser.parse(jobdetails['publication_date'])
        age = datetime.now() - created_at
        if age.days > 14:
            continue

        # If the listing is more recent, add it if we don't already have it in the database
        # https://stackoverflow.com/questions/2511679/python-number-of-rows-affected-by-cursor-executeselect
        check_if_job_exists(cursor, jobdetails)
        job_not_found = len(cursor.fetchall()) == 0
        if job_not_found:
            print("Adding new job to database!")
            add_new_job(cursor, jobdetails)
    print("Finished updating jobs")


def main():
    conn = connect_to_db()
    cursor = conn.cursor()
    create_tables(cursor)

    while (1):
        jobhunt(cursor)
        # Sleep for 1h
        time.sleep(21600)


# Sleep does a rough cycle count, system is not entirely accurate
# If you want to test if script works change time.sleep() to 10 seconds and delete your table in MySQL
if __name__ == '__main__':
    main()
