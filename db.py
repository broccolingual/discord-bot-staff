import psycopg2

import settings

def getConn():
    return psycopg2.connect(settings.DSN)

def createTables():
    conn = getConn()
    with conn.cursor() as cur:
        cur.execute("create table if not exists events (msg_id bigint primary key, event_id bigint, author_id bigint, created_at timestamp not null default now())")
        cur.execute("create table if not exists joined_users (event_id bigint, user_id bigint, created_at timestamp not null default now(), primary key(event_id, user_id))")
        conn.commit()
    conn.close()

def insertEvent(msg_id, event_id, author_id):
    conn = getConn()
    with conn.cursor() as cur:
        try:
            cur.execute("insert into events values (%s, %s, %s)", (msg_id, event_id, author_id))
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            print("insertEvent: already exists")
    conn.close()

def insertJoinedUser(event_id, user_id):
    conn = getConn()
    with conn.cursor() as cur:
        try:
            cur.execute("insert into joined_users values (%s, %s)", (event_id, user_id))
            conn.commit()
        except psycopg2.errors.UniqueViolation:
            print("insertJoinedUser: already exists")
    conn.close()

def deleteJoinedUser(event_id, user_id):
    conn = getConn()
    with conn.cursor() as cur:
        cur.execute("delete from joined_users where event_id = %s and user_id = %s", (event_id, user_id))
        conn.commit()
    conn.close()

def getEventID(msg_id):
    conn = getConn()
    values = None
    with conn.cursor() as cur:
        cur.execute("select event_id from events where msg_id = %s", (msg_id,))
        values = cur.fetchall()
    conn.close()
    if values is not None:
        print(f"getEventID: {values[0][0]}")
        return values[0][0]
    return None

def getJoinedUsers(event_id):
    conn = getConn()
    values = None
    with conn.cursor() as cur:
        cur.execute("select user_id from joined_users where event_id = %s", (event_id,))
        values = cur.fetchall()
    conn.close()
    if values is not None:
        print(f"getJoinedUsers: {[value[0] for value in values]}")
        return [value[0] for value in values]
    return None

def run():
    conn = getConn()
    values = conn.fetch("select version()")
    print(values)
    conn.close()

if __name__ == "__main__":
    run()