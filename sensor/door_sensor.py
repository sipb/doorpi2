import subprocess
import gpiozero
import pymysql
import signal
import time

def zwrite(zclass, instance, message, signature='I am but a door.', sender='host/sipb-defcon.mit.edu'):
    subprocess.run([
        'zwrite', '-q', '-U',
        '-S', sender, 
        '-s', signature,
        '-c', zclass,
        '-i', instance,
        '-m', message,
        ])

with open('/etc/doorpi') as fh:
    config = dict(zip(['host', 'user', 'passwd', 'db'], fh.read().splitlines()))

db = pymysql.connect(**config, use_unicode=True, autocommit=True)

def update_door_status(status):
    global db
    # For unknown reasons, Python won't flush stdout when it's connected to systemd's journal
    # unless you specifically tell it to
    print(f"About to update to {status}", flush=True)
    db.ping(reconnect=True)
    cursor = db.cursor()
    cursor.execute("INSERT INTO door_status(timestamp, status) VALUES (%s, %s)", (time.time_ns(), status))
    print(f"DB updated to {status}", flush=True)
    if status:
        zwrite('sipb-door', 'closed', 'The door is now closed.')
        zwrite('sipb-auto', 'door', 'The door is now closed.')
    else:
        zwrite('sipb-door', 'open', 'The door is now open.')
        zwrite('sipb-auto', 'door', 'The door is now open.')
    print(f"Zephyr updated to {status}", flush=True)

def get_door_status():
    global db
    print("About to fetch door status")
    db.ping(reconnect=True)
    cursor = db.cursor()
    cursor.execute("SELECT status FROM door_status ORDER BY timestamp DESC LIMIT 1")
    status = cursor.fetchone()
    if status is not None:
        status = bool(status[0])
    
    return status

# The door sensor is a hall sensor, which is not exactly a button, but it is close enough
door_sensor = gpiozero.Button("GPIO4")

door_sensor.when_pressed = lambda: update_door_status(True)
door_sensor.when_released = lambda: update_door_status(False)

# In case the door status changed while the daemon was offline for some reason, make sure
# the current status in the database is correct
current_status = door_sensor.is_pressed
if current_status != get_door_status():
    update_door_status(current_status)

# Everything else we need to do is handled via callbacks, so just pause forever
signal.pause()
