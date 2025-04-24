import socket

# config
server_address = ("127.0.0.1", 12345)
bufferSize = 1024

# socket -- client side
client_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

print("client ready!")

# comms to server - send to server, receive from broadcast
while True:
    msg_from_client = input("> ")
    client_socket.sendto(msg_from_client.encode(), server_address)

    try:
        data, address = client_socket.recvfrom(bufferSize)
        if address != server_address:
            print(f"{address}: {data.decode()}")
    except socket.error as e:
        print(e)