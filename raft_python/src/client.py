from raft.raft_pb2 import ServeClientArgs, ServeClientReply
from raft.raft_pb2_grpc import RaftStub
import grpc
import click
import random
from raft_initializer import cluster_config
# Client class to interact with the Raft server
class Client:

    def __init__(self):
        self.peers = cluster_config['peers']
        self.leader_config = None

    def serve(self, data) -> ServeClientReply:
        while True:
            try:
                if self.leader_config is None:
                    self.leader_config = random.choice(self.peers)
                    print("Opting for a random leader: ", self.leader_config['id'])

                self.address = f"{self.leader_config['host']}:{self.leader_config['port']}"
                print("Sendng over Address: ", self.address)
                
                with grpc.insecure_channel(self.address) as channel:
                    stub = RaftStub(channel)
                    args = ServeClientArgs(Request=data)
                    response: ServeClientReply = stub.ServeClient(args)

                    success = response.Success
                    msg = response.Data
                    leader_id = response.LeaderID

                    print("Data sent successfully")
                    print("Response: ", msg)

                    if success:
                        print(f"Leader ID: {self.leader_config['id']}")
                        break

                    else:
                        if leader_id:
                            self.update_leader(leader_id)
                            print(f"Leader ID: {leader_id}")
                        else:
                            self.leader_config = None

                        print("Data sending failed")
                    print()
            except KeyboardInterrupt:
                print("Exiting...")
                exit(0)
            except Exception:
                print("Error occurred. Retrying...")
                self.leader_config = None

        return
        
    def update_leader(self, leader_id):
        self.leader_config = [peer for peer in self.peers if peer['id'] == leader_id][0]

    def getInput(self, message, range=None)-> int:
        while True:
            try:
                inp = int(input(message))
                if range is not None:
                    if inp in range:
                        return inp
                    else:
                        raise ValueError("Invalid input. Please try again.")
                else:
                    return inp
            
            except KeyboardInterrupt:
                print("Exiting...")
                exit(0)

            except:
                print("Invalid input. Please try again.")


    def getChoice(self):
        optionString = """
1. Send Data
2. Exit
        """     
        
        print(optionString)
        try:
            choice = self.getInput("Enter your choice: ", range(1, 7))
            return choice
        except KeyboardInterrupt:
            print("Exiting...")
            exit(0)


    def client_serve(self):
        choice = self.getChoice()
        if choice == 1:
            command_set = """
1. SET
2. GET
"""
            print(command_set)
            try:
                choice = self.getInput("Enter your choice: ", range(1, 3))
            except KeyboardInterrupt:
                print("Exiting...")
                exit(0)

            if choice == 1:
                key = input("Enter key: ")
                value = input("Enter value: ")
                if not key or not value:
                    print("Please enter some values.")
                    return

                data = f"SET {key} {value}"
                print("Sending Command: ", data)
                self.serve(data)

            elif choice == 2:
                key = input("Enter key: ")
                data = f"GET {key}"

                if not key:
                    print("Please enter some values.")
                    return 
                
                print("Sending Command: ", data)
                self.serve(data)
            else:
                print("Invalid choice")
    
        elif choice == 2:
            exit(0)
        else:
            print("Invalid choice")
 

def main():
    client = Client()

    try:
        while True:
            client.client_serve()

    except KeyboardInterrupt:
        print('Exiting...')


if __name__ == '__main__':
    main()
