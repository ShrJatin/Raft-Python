# Raft implementation in Python using gRPC
This is a standalone implementation of Raft, incorporating Leader lease functionality for faster, serializable reads. The timers for heartbeat, leader lease and election are handled in real-time using threads, and communication between servers and clients is handled using gRPC.

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
