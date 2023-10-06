#!/usr/bin/python3

import pymysql
from datetime import datetime, timedelta
from math import trunc
from time import time_ns
from typing import List

config_file = open("/etc/doorpi").read().splitlines()
config = {
    "host": config_file[0],
    "user": config_file[1],
    "passwd": config_file[2],
    "db": config_file[3],
}

db = pymysql.connect(**config, use_unicode=True, autocommit=True)
cursor = db.cursor()

def prob_open(start: datetime, end: datetime, splits: int) -> List[float]:
    # Timestamps in the database are stored in ns
    start = trunc(start.timestamp()) * 10**9
    end = trunc(end.timestamp()) * 10**9

    split_size = (end - start) // splits

    cursor.execute("SELECT timestamp, status FROM door_status WHERE %s < timestamp AND timestamp < %s ORDER BY timestamp ASC", (start, end))
    relevant = list(cursor.fetchall())

    cursor.execute("SELECT timestamp, status FROM door_status WHERE timestamp <= %s ORDER BY timestamp DESC LIMIT 1", (start,))
    first_before = cursor.fetchone()
    if first_before is None:
        # Assume that the door was closed if there is no data
        first_before = True
    else:
        first_before = first_before[1]

    relevant.extend((start + split_size * i, None) for i in range(1, splits + 1))
    # mark the door as shut for any time past now
    relevant.append((time_ns(), 2))
    relevant.sort()

    open_time = 0
    closed_time = 0
    probs = []

    prev_status = first_before
    prev_time = start
    for (timestamp, status) in relevant:
        if status == prev_status:
            # Ignore spurious data
            continue
        
        delta = timestamp - prev_time

        if prev_status == 1:
            closed_time += delta
        elif prev_status == 0:
            open_time += delta
        else: pass

        if status is None:
            # Split marker
            clopen_time = open_time + closed_time
            probs.append(open_time / clopen_time if clopen_time > 0 else None)
            open_time = 0
            closed_time = 0

            prev_time = timestamp
        else:
            prev_status = status
            prev_time = timestamp

    return probs

from flask import Flask, request, render_template

app = Flask(__name__)

@app.before_request
def before_request():
    db.ping(reconnect=True)

@app.route("/")
def index():
    cursor.execute("SELECT timestamp, status FROM door_status ORDER BY timestamp DESC LIMIT 1")
    timestamp, status = cursor.fetchone()

    # timestamp is in nanoseconds, but datetime can only handle timestamps with seconds
    last_change = datetime.fromtimestamp(timestamp // 10**9)

    # XXX: It seems that timedelta has some strange behavior that I can't explain
    # >>> from datetime import datetime, timedelta
    # >>> now = datetime.now()
    # >>> day_ago = now - timedelta(days=1)
    # >>> week_ago = now - timedelta(days=7)
    # >>> (now.timestamp() - week_ago.timestamp()) / 7
    # 86914.28571428571
    # >>> (now.timestamp() - day_ago.timestamp())
    # 86400.0
    # >>> (86914.28571428571 - 86400.0) / 60
    # 8.571428571428502
    #
    # Why are there 8.57 extra minutes???

    now = datetime.now()
    monday_t = now - timedelta(days=now.weekday())
    monday = datetime(monday_t.year, monday_t.month, monday_t.day)

    nmonday = monday + timedelta(days=7)

    hourly = prob_open(monday, nmonday, 24 * 7)

    fuzzball_image = f"static/eyes_{'closed' if status else 'open'}.png"
    door_status = "closed" if status else "open"
    prob_color = [None if prob is None else (trunc(prob * 100), 100 - trunc(prob * 25)) for prob in hourly]
    return render_template("index.html",
            fuzzball_image=fuzzball_image,
            door_status=door_status,
            last_change=last_change,
            monday=monday.date(),
            prob_color=prob_color,
        )

@app.route("/text")
def text():
    cursor.execute("SELECT timestamp, status FROM door_status ORDER BY timestamp DESC LIMIT 1")
    timestamp, status = cursor.fetchone()

    # timestamp is in nanoseconds, but datetime can only handle timestamps with seconds
    last_change = datetime.fromtimestamp(timestamp // 10**9)

    return f"{'Closed' if status else 'Open'} since {last_change}"

@app.route("/embed")
def embed():
    cursor.execute("SELECT timestamp, status FROM door_status ORDER BY timestamp DESC LIMIT 1")
    timestamp, status = cursor.fetchone()

    # timestamp is in nanoseconds, but datetime can only handle timestamps with seconds
    last_change = datetime.fromtimestamp(timestamp // 10**9)

    fuzzball_image = f"static/eyes_{'closed' if status else 'open'}.png"
    door_status = "closed" if status else "open"

    return render_template("embed.html",
            fuzzball_image=fuzzball_image,
            door_status=door_status,
            last_change=last_change,
        )
