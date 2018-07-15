#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import signal
import requests
import urllib3
import json
import datetime
from gi import require_version

require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk

require_version('AppIndicator3', '0.1')
from gi.repository import AppIndicator3 as appindicator

# require_version('GLib', '??')
from gi.repository import GLib

APPINDICATOR_ID = 'sensor-indicator'
menu_icon_name = "blank_pixel_column.png"
host = "orangepi2"
port = 4040
update_interval = 60
temp_units = 'F'

indicator = None
menu = None
last_updated = None

verbose_log = {'verbose': sys.stderr}

def get_temp_humidity(units='C'):
    try:
        r = requests.get("http://"+host+":"+str(port)+"/temp?units="+str(temp_units), timeout=20)
        if r.status_code != 200:
            print("Request returned with error code {:d}".format(r.status_code))
            return (None, None)
    except Exception as err:
        if type(err.args[0]) is not urllib3.exceptions.MaxRetryError: # Connection refused (??)
            print("{} occurred: -{}- {}".format(type(err).__name__, type(err.args[0]), err))
        else:
            print("Unidentified Exception occurred when GETing data.")
        return (None, None)

    data = json.loads(r.text)
    if data['temperature_units'] != units:
        print("Request returned data not matching requested temperature units.")
        print("  Requested: {:s}\n  Returned: {:s}".format(units, data['temperature_units']))

    # maybe this should also return the actual returned units?
    return (data['temperature'], data['humidity'])

def build_menu():
    global last_updated
    menu = gtk.Menu()
    item_update = gtk.MenuItem('Update')
    item_update.connect('activate', update_sensors)
    menu.append(item_update)
    item_last_updated = gtk.MenuItem("    [Last updated {:s}]".format(last_updated.strftime("%H:%M:%S")
                                                                      if last_updated else "Never"))
    menu.append(item_last_updated)
    menu.append(gtk.SeparatorMenuItem())

    led_submenu = gtk.Menu()
    led_full = gtk.MenuItem('Full')
    led_full.connect('activate', set_led, 'window', 1023)
    led_submenu.append(led_full)
    led_half = gtk.MenuItem('Half')
    led_half.connect('activate', set_led, 'window', 512)
    led_submenu.append(led_half)
    led_dim = gtk.MenuItem('Dim')
    led_dim.connect('activate', set_led, 'window', 192)
    led_submenu.append(led_dim)
    led_off = gtk.MenuItem('Off')
    led_off.connect('activate', set_led, 'window', 0)
    led_submenu.append(led_off)
    led_submenu.append(gtk.SeparatorMenuItem())
    led_up = gtk.MenuItem('Up')
    led_up.connect('activate', adjust_led, 'window', 128)
    led_submenu.append(led_up)
    led_down = gtk.MenuItem('Down')
    led_down.connect('activate', adjust_led, 'window', -128)
    led_submenu.append(led_down)

    window_led = gtk.MenuItem('Window LEDs')
    window_led.set_submenu(led_submenu)
    menu.append(window_led)
    menu.append(gtk.SeparatorMenuItem())

    item_quit = gtk.MenuItem('Quit')
    item_quit.connect('activate', quit)
    menu.append(item_quit)
    menu.show_all()
    return menu

def update_sensors(source=None):
    global indicator, last_updated
    temp, humidity = get_temp_humidity(temp_units)
    if temp != None or humidity != None:
        indicator.set_label("{:.1f}º{:s} / {:.1f}%".format(temp, temp_units, humidity),
                            "100.0ºC / 100.0%")
        last_updated = datetime.datetime.now()
        # DEBUG
        print("Updated to [{:.1f}, {:.1f}] at {:s}".format(temp, humidity,
                                                           last_updated.strftime("%H:%M:%S")))
    else:
        if last_updated == None or (datetime.datetime.now() - last_updated > datetime.timedelta(hours=1)):
            indicator.set_label("--º{:s} / --%".format(temp_units),
                                "100.0ºC / 100.0%")
        # DEBUG
        print("Could not update at {:s}".format(datetime.datetime.now().strftime("%H:%M:%S")))

    indicator.set_menu(build_menu())
    return True

def set_led(source=None, led_name="null", brightness=0):
    data = {'brightness': brightness}
    #try:
    r = requests.put("http://"+host+":"+str(port)+"/leds/"+led_name, json=data)
    if r.status_code != 200:
        print("Got code {}".format(r.status_code))
        return False
    response_data = r.json()
    if response_data['target'] != brightness:
        print("Target brightness returned ({}) does not equal brightness requested ({})".format(response_data['target'], brightness))
        return False
    return True

def adjust_led(source=None, led_name="null", change=0):
    #try:
    r = requests.get("http://"+host+":"+str(port)+"/leds/"+led_name)
    if r.status_code != 200:
        print("Got code {}".format(r.status_code))
        return False
    response_data = r.json()
    # If currently fading, add adjustment to end of fade
    target_brightness = response_data['target']
    new_brightness = target_brightness + change
    return set_led(None, led_name, new_brightness)

def quit(source=None):
    gtk.main_quit()

def main():
    global indicator, menu
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    menu_icon_path = os.path.abspath(os.path.dirname(os.path.realpath(__file__))+"/resources/"+menu_icon_name)
    indicator = appindicator.Indicator.new(APPINDICATOR_ID, menu_icon_path,
                                           appindicator.IndicatorCategory.HARDWARE)
                                           # category influences indicator order - try others
    indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
    indicator.set_menu(build_menu())
    indicator.set_label("--ºF / --%", "100.0ºC / 100.0%")

    # Set up automatic updates
    GLib.timeout_add_seconds(update_interval, update_sensors)
    # Force first update
    update_sensors()

    gtk.main()


if __name__ == '__main__':
    main()
