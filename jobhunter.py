# Drake Costa
# CNE340 Fall 2023
#
# Job Hunter project. Scrapes remotive for job listings and adds them to a MySQL database.
# Adapted from https://github.com/ellisju37073/cne340_jobhunter/blob/master/jobhunter.py
#
# Using docker compose configuration from
# https://stackoverflow.com/questions/75967671/python-mysql-connector-python-how-to-connect-to-docker-container-from-terminal

import os
import mysql.connector
import time
import json
import requests
from datetime import date, datetime, timedelta
import dateutil.parser
import html2text


def connect_to_db():
    conn = mysql.connector.connect(
        user=os.environ['MYSQL_USER'],
        password=os.environ['MYSQL_PASSWORD'],
        database=os.environ['MYSQL_DATABASE'],
        host=os.environ['MYSQL_HOST'],
        port=int(os.environ['MYSQL_PORT'])
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


def check_if_job_exists(cursor, jobdetails) -> bool:
    query = """
        SELECT COUNT(1) FROM jobs WHERE job_id = %s;
    """
    job_id = jobdetails["id"]
    cursor.execute(query, (job_id,))
    if cursor.fetchone()[0]:
        print(f"Job {job_id} already exists")
        return True


def delete_old_jobs(cursor):
    query = """
        DELETE FROM jobs WHERE created_at > curdate() - interval 14 day;
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
    total = 0
    for jobdetails in jobpage['jobs']:
        # First check if the job listing is older than 14 days, skip if true
        created_at = dateutil.parser.parse(jobdetails['publication_date'])
        age = datetime.now() - created_at
        if age.days > 14:
            continue

        # If the listing is more recent, add it if we don't already have it in the database
        if not check_if_job_exists(cursor, jobdetails):
            print("Adding new job to database!")
            add_new_job(cursor, jobdetails)
            total += 1
    print(f"Finished updating, added {total} jobs")

def log_row_count(cursor):
    cursor.execute("SELECT COUNT(*) FROM jobs")
    count = cursor.fetchone()[0]
    print(f"{count} total jobs")


def main():
    conn = connect_to_db()
    cursor = conn.cursor()
    create_tables(cursor)
    log_row_count(cursor)

    while (1):
        jobhunt(cursor)
        conn.commit()
        log_row_count(cursor)
        cursor.execute("SELECT title, created_at from jobs LIMIT 100;")
        rows = cursor.fetchall()
        print(*rows,sep='\n')
        # Sleep for 1h
        time.sleep(21600)


# Sleep does a rough cycle count, system is not entirely accurate
# If you want to test if script works change time.sleep() to 10 seconds and delete your table in MySQL
if __name__ == '__main__':
    main()
