import click
from raft_server import RaftServer


cluster_config = {
        "id": 1,
        "cluster_name": "test-cluster",
        "election_timeout_min": 5,
        "election_timeout_max": 10,
        "heartbeat_interval": 0.5,
        "lease_interval": 5,
        "peers": [
            {
                "id": 1,
                "host": "127.0.0.1",
                "port": 9001
            },
            {
                "id": 2,
                "host": "127.0.0.1",
                "port": 9002
            },
            {
                "id": 3,
                "host": "127.0.0.1",
                "port": 9003
            },
            {
                "id": 4,
                "host": "127.0.0.1",
                "port": 9004
            },
            {
                "id": 5,
                "host": "127.0.0.1",
                "port": 9005
            }
        ]
    }

@click.command()
@click.argument('node_id', type=int)
def main(node_id):
    """
    This script is used to initialize a raft cluster.
    """
    # try:
    raft_initializer = RaftServer(node_id, cluster_config)
    raft_initializer.start()
        
    # except Exception as e:
    #     print(e)



if __name__ == '__main__':
    main()


# 1> 


