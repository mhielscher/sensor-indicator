#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import signal
import requests
import json
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

def get_temp_humidity(units='C'):
    r = requests.get("http://"+host+":"+str(port)+"/temp?units="+str(temp_units))
    if r.status_code != 200:
        print("Request returned with error code {:d}".format(r.status_code))
        return (0, 0)

    data = json.loads(r.text)
    if data['temperature_units'] != units:
        print("Request returned data not matching requested temperature units.")
        print("  Requested: {:s}\n  Returned: {:s}".format(units, data['temperature_units']))

    # maybe this should also return the actual returned units?
    return (data['temperature'], data['humidity'])

def build_menu():
    menu = gtk.Menu()
    item_update = gtk.MenuItem('Update')
    item_update.connect('activate', update_sensors)
    menu.append(item_update)
    item_quit = gtk.MenuItem('Quit')
    item_quit.connect('activate', quit)
    menu.append(item_quit)
    menu.show_all()
    return menu

def update_sensors(source=None):
    global indicator
    temp, humidity = get_temp_humidity(temp_units)
    indicator.set_label("{:.1f}º{:s} / {:.1f}%".format(temp, temp_units, humidity),
                        "100.0ºC / 100.0%")

def quit(source=None):
    gtk.main_quit()

def main():
    global indicator
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

    gtk.main()


if __name__ == '__main__':
    main()
