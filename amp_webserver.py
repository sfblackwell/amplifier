# Base on the code for:
https://learn.adafruit.com/pico-w-http-server-with-circuitpython/code-the-pico-w-http-server
#
# SPDX-FileCopyrightText: 2022 Liz Clark for Adafruit Industries
#
# SPDX-License-Identifier: MIT
#
# Modified by Simon F Blackwell, appologies but I am no coder !

import os
import time
import ipaddress
import wifi
import socketpool
import busio
import board
import microcontroller
import displayio
import terminalio
from adafruit_display_text import label
import adafruit_imageload
import digitalio # import DigitalInOut, Direction
from adafruit_httpserver.server import HTTPServer
from adafruit_httpserver.response import HTTPResponse
import neopixel
import rotaryio

#	look for amplifier
try:
    i2c = busio.I2C(board.GP9, board.GP8)
    amp = adafruit_max9744.MAX9744(i2c)
    amp.volume = 0
    ampFound = True
    print("Amp Found")
except:
    ampFound = False 
    print("No Amp Found")

#	Volume functions     
def VolumeUp(volume1, position1change):

        print("Volume Up",position1change)

        volume1 = volume1 + position1change
        if volume1 > 63:
            volume1 = 63
        volume1change = volume1 - last1Volume
        for _ in range(volume1change):
            if ampFound:
                amp.volume_up()

        print("New volume", volume1)
        
        setPixels(volume1)
        
        return volume1

def VolumeDown(volume1, position1change):
    
        print("Volume Down",position1change)
    
        volume1 = volume1 + position1change
        if volume1 <0:
            volume1 = 0
        volume1change = volume1 - last1Volume
        for _ in range(-volume1change):
            if ampFound:
                amp.volume_down()
                
        print("New volume", volume1)
        
        setPixels(volume1)
        
        return volume1
    
def setVolume(volume1):

        print("Volume Mute")
        if ampFound:
            amp.volume = volume1        
       
        print("New volume", volume1)
        
        setPixels(volume1)
        
        return volume1 

#	setup neopixels
pixelOffset = 0

def setPixels(volume1):

        volDivMod = divmod(volume1,8)
        print(volDivMod)
        
        for x in range(0, 8):
            pixels[x] = (0,0,0)
        if volume1 == 0:
                pixels.show()
                return
            
        for x in range(0, volDivMod[0]+1):
            pixels[x] = colourArray[x]
            print("Pixel",x,"Color Array",colourArray[x])
            
        pixels.show()
                  
colourArray = [
            (0, 255, 0),
            (0, 255, 0),
            (0, 255, 0),
            (0, 255, 0),
            (255, 128, 0),
            (255, 128, 0),
            (255, 0, 0),
            (255, 0, 0)]

pixels = neopixel.NeoPixel(board.GP5, 24, brightness=0.1,auto_write=False)

#	show first and last pixel
pixels.fill((0, 0, 0))
pixels.show()
pixels[0]=(0, 255, 0)
pixels[7]=(0, 0, 255)
pixels.show()
   
#	set up rotary encoder   
encoder1 = rotaryio.IncrementalEncoder(board.GP0, board.GP1)
last1position = 0
rot1Button = digitalio.DigitalInOut(board.GP2)
rot1Button.switch_to_input(pull=digitalio.Pull.UP)
volume1 = 0
last1Volume = 0

#	setup webserver

#  connect to network
print()
print("Connecting to WiFi")

#  set static IP address
ipv4 =  ipaddress.IPv4Address("192.168.1.42")
netmask =  ipaddress.IPv4Address("255.255.255.0")
gateway =  ipaddress.IPv4Address("192.168.1.1")
wifi.radio.set_ipv4_address(ipv4=ipv4,netmask=netmask,gateway=gateway)
#  connect to your SSID
wifi.radio.connect(os.getenv('WIFI_SSID'), os.getenv('WIFI_PASSWORD'))

print("Connected to WiFi")
pool = socketpool.SocketPool(wifi.radio)
server = HTTPServer(pool)

#  variables for HTML
#  comment/uncomment desired temp unit

#  font for HTML
font_family = "monospace"

#  the HTML script
#  setup as an f string
#  this way, can insert string variables from code.py directly
#  of note, use {{ and }} if something from html *actually* needs to be in brackets
#  i.e. CSS style formatting
def webpage():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta http-equiv="Content-type" content="text/html;charset=utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    html{{font-family: {font_family}; background-color: lightgrey;
    display:inline-block; margin: 0px auto; text-align: center;}}
      h1{{color: deeppink; width: 200; word-wrap: break-word; padding: 2vh; font-size: 35px;}}
      p{{font-size: 1.5rem; width: 200; word-wrap: break-word;}}
      .button{{font-family: {font_family};display: inline-block;
      background-color: black; border: none;
      border-radius: 4px; color: white; padding: 16px 40px;
      text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}}
      p.dotted {{margin: auto;
      width: 75%; font-size: 25px; text-align: center;}}
    </style>
    </head>
    <body>
    <title>Amplifier Control Web Server</title>
    <p class="dotted">The current volume is
    <span style="color: deeppink;">{webVolume}</span></p><br>
    <p>Control the volume with these buttons:</p><br>
    <form accept-charset="utf-8" method="POST">
    <button class="button" name="VOLUME UP" value="VOLUME UP" type="submit">Volume Up</button></a></p></form>
    <p><form accept-charset="utf-8" method="POST">
    <button class="button" name="VOLUME DOWN" value="VOLUME DOWN" type="submit">Volume Down</button></a></p></form>
    <p><form accept-charset="utf-8" method="POST">
    <button class="button" name="MUTE" value="MUTE" type="submit">Mute</button></a></p></form>
    
    <p><form accept-charset="utf-8" method="POST">
    Set Volume:
    <input type="range" name="SLIDER" min="0" max="63" value="{webVolume}">
    <button class="button" name="SUBMIT" value="SUBMIT" type="submit">Submit</button></a></p>
    </form>
    </body></html>
    """
    return html


#  route default static IP
@server.route("/")
def base(request):  # pylint: disable=unused-argument
    #  serve the HTML f string
    #  with content type text/html
    return HTTPResponse(content_type="text/html", body=webpage())



#  if a button is pressed on the site
@server.route("/", "POST")
def buttonpress(request):
    
    global volume1
    
    #  get the raw text
    
    raw_text = request.raw_request.decode("utf8")
    print("***"+raw_text+"***")
    if "VOLUME+UP" in raw_text:
        print("Volume Up")
        volume1 = VolumeUp(volume1, 4)
    elif "VOLUME+DOWN" in raw_text:
        print("Volume Down")
        volume1 = VolumeDown(volume1, -4)
    elif "MUTE" in raw_text:
        print("Volume Mute")
        volume1 = setVolume(0)
    elif "SLIDER=" in raw_text:
        sliderPos = raw_text.index("SLIDER=")+7
        sliderRight = raw_text[sliderPos:]          
        andPos = sliderRight.index("&")
        sliderStr = sliderRight[:andPos]
        sliderVal = int(sliderStr)     
        volume1 = setVolume(sliderVal)
        

    return HTTPResponse(content_type="text/html", body=webpage())

print("starting server..")
# startup the server
try:
    server.start(str(wifi.radio.ipv4_address))
    print("Listening on http://%s:80" % wifi.radio.ipv4_address)
    #  if the server fails to begin, restart the pico w
except OSError:
    time.sleep(5)
    os._exit()
#    print("restarting..")
#    microcontroller.reset()
    
ping_address = ipaddress.ip_address("8.8.4.4")

clock = time.monotonic() #  time.monotonic() holder for server ping

#
#	main loop

while True:
    try:
        
        #	volume control code
       
        position1 = encoder1.position
        position1change = position1 - last1position
        if position1change > 0:
            volume1 = VolumeUp(volume1, position1change)
        elif position1change < 0:
            volume1 = VolumeDown(volume1, position1change)
        if rot1Button.value == False:
            volume1 = setVolume(0)           
            
        last1Volume = volume1
        last1position = position1
               
        #  every 30 seconds, ping server & update temp reading
        webVolume = last1Volume
        
        if (clock + 30) < time.monotonic():
            if wifi.radio.ping(ping_address) is None:
                print("lost connection")
            else:
                print("connected")
            clock = time.monotonic()
             
        #  poll the server for incoming/outgoing requests
        server.poll()
    # pylint: disable=broad-except
    except Exception as e:
        print(e)
        time.sleep(5)
        continue
