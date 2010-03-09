#
# BigBrotherBot(B3) (www.bigbrotherbot.com)
# Copyright (C) 2005 Michael "ThorN" Thornton
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
#
# CHANGELOG
# 2010/03/09 - 0.5 - Courgette
# * open a TCP connection to a BFBC2 server, auth with provided password
# * can either be used to send commands or enter the listening mode (which
#   waits for BFBC2 events)
#

__author__  = 'Courgette'
__version__ = '0.5'

debug = True

import time
import socket
from b3.parsers.bfbc2.EventConsole import *

class Bfbc2Exception(Exception): pass
class Bfbc2BadPasswordException(Bfbc2Exception): pass
class Bfbc2BadCommandException(Bfbc2Exception): pass

class Bfbc2Connection(object):
    
    _serverSocket = None
    _host = None
    _port = None
    _password = None

    _maxShortRetryCount = 10
    _maxLongRetryCount = 10
    _delayBetweenLongRetry = 5 # seconds
    _timeout = 30

    def __init__(self, host, port, password):
        
        self._host = host
        self._port = port
        self._password = password
        
        self._connect()
        self._auth()
   
    def __set_timeout(self, value):
        if value is not None and value < 0:
            self._timeout = 0
        else:
            self._timeout = value
        if self._serverSocket is not None:
            self._serverSocket.settimeout(self._timeout)
   
    def _connect(self):
        try:
            self._serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._serverSocket.connect( ( self._host, self._port ) )
            self._serverSocket.setblocking(1)
            self._serverSocket.settimeout(self._timeout)
        except Exception, err:
            raise Bfbc2Exception(err)
    
    def close(self):
        if self._serverSocket is not None:
            self._serverSocket.close()

    def sendRequest(self, command, *args):
        words = [command]
        words += args
        request = EncodeClientRequest(words)
        printPacket(DecodePacket(request))
        self._serverSocket.send(request)
        response = self._serverSocket.recv(4096)
        decodedResponse = DecodePacket(response)
        printPacket(decodedResponse)
        #[isFromServer, isResponse, sequence, words] = decodedResponse
        return decodedResponse[3]
        
    def _auth(self):
        # Retrieve this connection's 'salt' (magic value used when encoding password) from server
        words = self.sendRequest("login.hashed")

        # if the server doesn't understand "login.hashed" command, abort
        if words[0] != "OK":
            raise Bfbc2Exception("Could not retrieve salt")

        # Given the salt and the password, combine them and compute hash value
        salt = words[1].decode("hex")
        passwordHash = generatePasswordHash(salt, self._password)
        passwordHashHexString = string.upper(passwordHash.encode("hex"))

        # Send password hash to server
        loginResponse = self.sendRequest("login.hashed", passwordHashHexString)

        # if the server didn't like our password, abort
        if loginResponse[0] != "OK":
            raise Bfbc2BadPasswordException("The BFBC2 server refused our password")

            
    def subscribeToBfbc2Events(self):
        """
        tell the bfbc2 server to send us events
        """
        response = self.sendRequest("eventsEnabled", "true")

        # if the server didn't know about the command, abort
        if response[0] != "OK":
            raise Bfbc2BadCommandException(response[1:])

        
    def handle_bfbc2_events(self):
        # Wait for packet from server
        packet = self._serverSocket.recv(4096)    
        [isFromServer, isResponse, sequence, words] = DecodePacket(packet)
        printPacket(DecodePacket(packet))
        
        # If this was a command from the server, we should respond to it
        # For now, we always respond with an "OK"
        if isResponse:
            print 'Received an unexpected response packet from server, ignoring'
            return self.waitForEvent()
        else:
            response = EncodeClientResponse(sequence, ["OK"])
            printPacket(DecodePacket(response))
            self._serverSocket.send(response)
            return words
            

        


###################################################################################
# Display contents of packet in user-friendly format, useful for debugging purposes
def printPacket(packet):
    if debug:
        if (packet[0]):
            print ">",
        else:
            print "<",
        
        if (packet[1]):
            print "R",
        else:
            print "Q",
    
        print "(%s)" %  packet[2],
    
        if packet[3]:
            print " :",
            for word in packet[3]:
                print "\"" + word + "\"",
    
        print ""
    
###################################################################################
# Example program

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 4:
        host = raw_input('Enter game server host IP/name: ')
        port = int(raw_input('Enter host port: '))
        pw = raw_input('Enter password: ')
    else:
        host = sys.argv[1]
        port = int(sys.argv[2])
        pw = sys.argv[3]
        
    bc2server = Bfbc2Connection(host, port, pw)
    
    