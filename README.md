# Raft implementation in Python using gRPC
This is a standalone implementation of Raft, incorporating Leader lease functionality for faster, serializable reads. The timers for heartbeat, leader lease and election are handled in real-time using threads, and communication between servers and clients is handled using gRPC. The default implementation runs 5 server nodes on localhost, and the code can be extended to serve any number of servers. This can also be hosted on Google Cloud platform by providing suitable IP addresses and port numbers. 

# Installation
## Setting up source code
1. Create a new python environment using pip or conda, and activate it.
2. Install poetry using pip install poetry
3. Clone this repository
4. cd to the raft_python directory
5. Use command "poetry install" to install all the project dependencies

## Setting up wheel file
1. git clone this repository
2. cd to the dist directory
3. pip install *.whl
   
# Running
## Running using source code
1. Use the command "poetry run Raft-initializer <id>" where id ranges from 1, 2 ... , 5 to run the Raft server nodes
2. Use the command "poetry run client" to run the Raft client. 
