import socket

# config
localIP = "127.0.0.1"
localPort = 12345
bufferSize = 1024
msgFromServer = "Hello Client"
bytesToSend = str.encode(msgFromServer)

# socket -- server side
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))
print("server up")

# Listen for incoming datagrams
while True:
    bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
    message = bytesAddressPair[0]
    address = bytesAddressPair[1]

    clientMsg = "Message from Client:{}".format(message)
    clientIP = "Client IP Address:{}".format(address)

    print(clientMsg)
    print(clientIP)

    # replying to client
    UDPServerSocket.sendto(bytesToSend, address)