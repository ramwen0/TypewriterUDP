import socket

# config
msgFromClient = "client connected"
bytesToSend = str.encode(msgFromClient)
serverAddressPort = ("127.0.0.1", 12345)
bufferSize = 1024

# socket -- client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) # IPV4, UDP

# comms to server -- only prints once
count = 0
while count < 1:
    UDPClientSocket.sendto(bytesToSend, serverAddressPort)
    msgFromServer = UDPClientSocket.recvfrom(bufferSize)
    msg = "Message from Server {}".format(msgFromServer[0])
    print(msg)
    count += 1