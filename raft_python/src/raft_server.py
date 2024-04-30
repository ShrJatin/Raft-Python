import random
import time
import grpc
import os
from raft.raft_pb2 import *
from raft.raft_pb2_grpc import *
from concurrent import futures
from multiprocessing import Process
from commit_log import CommitLog
from threading import Thread
from multiprocessing.pool import ThreadPool
from multiprocessing import Process, Manager, Queue


PATH = os.path.dirname(os.path.abspath(__file__))


# RaftServer class represents a single Raft server.
class RaftServer(RaftServicer):

    FOLLOWER_ENUM = 0
    CANDIDATE_ENUM = 1
    LEADER_ENUM = 2

    def __init__(self, node_id, cluster_config):

        self.cluster_config = cluster_config
        self.node_id = node_id
        self.log_folder_path = self.create_log_folder()
        self.commit_log = CommitLog(self.node_id, self.log_folder_path)

        self.ip = [peer['host'] for peer in self.cluster_config['peers'] if peer['id'] == self.node_id][0]
        self.port = [peer['port'] for peer in self.cluster_config['peers'] if peer['id'] == self.node_id][0]
        self.channel = f"{self.ip}:{self.port}"

        self.heartbeat_interval = self.cluster_config['heartbeat_interval']
        self.election_timeout = random.randint(self.cluster_config['election_timeout_min'], self.cluster_config['election_timeout_max'])
        self.lease_interval = self.cluster_config['lease_interval']

        self.last_time_heartbeat = time.time()
        self.stop_election_timeout = False

        self.leader_lease_timeout = 0
        self.start_timestamp_leader_lease = time.time()
        self.maximum_remaining_lease = 0
    
        self.state = 'follower'
        self.leader_id = None

        self.term, self.commit_index, self.voted_for = self.commit_log.read_metadata()
        
        self.last_indices = {peer['id']: -1 for peer in self.cluster_config['peers']}
        self.match_indices = {peer['id']: -1 for peer in self.cluster_config['peers']}

        self.databasee = self.commit_log.read_database()
        self.read_queue = Queue()
        self.reply_queue = Queue()

        print("Election Timeout Set to:", self.election_timeout)
        print("Heartbeat Interval Set to:", self.heartbeat_interval)
        print("Leader Lease Timeout Set to:", self.lease_interval)
        print()
    
    def create_log_folder(self):
        log_folder_path = PATH + f"/logs_node_{self.node_id}"
        if not os.path.exists(log_folder_path):
            os.makedirs(log_folder_path)
        return log_folder_path

    def serve(self):
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        add_RaftServicer_to_server(self, self.server)
        self.server.add_insecure_port(f'[::]:{self.port}')
        self.server.start()
        print(f"Raft Server node_id: {self.node_id} listeing on address: {self.ip}:{self.port}")

        self.server.wait_for_termination()


    def assign_role(self, role='follower'):
        while True:
            role = self.state
            # print(f"Raft Server node_id: {self.node_id} started for role {self.state} on address: {self.ip}:{self.port}")
            if role == 'leader':
                self.commit_log.dump_print(f"Node {self.node_id} became the leader for term {self.term}.")
                self.commit_log.dump_print(f"New Leader waiting for Old Leader Lease to timeout.")
                self.wait_for_lease_timeout()
                self.start_leader()

            elif role == 'follower':
                self.start_follower()   

            elif role == 'candidate':
                self.start_candidate()

    
    def wait_for_lease_timeout(self):
        # print(self.leader_lease_timeout, "in wait_for_lease_timeout", self.election_timeout)
        while self.leader_lease_timeout > 0:
            time.sleep(max(self.leader_lease_timeout, 0))
        self.leader_lease_timeout = 0
        return

    def start_follower(self):
        self.last_time_heartbeat = time.time()
        self.start_election_timeout()
        # print(f"Raft Server node_id: {self.node_id} stopped for role {self.state} on address: {self.ip}:{self.port}")
        self.state = 'candidate'    
        return

    def start_election_timeout(self):
        self.stop_election_timeout = False
        self.election_timeout = random.randint(self.cluster_config['election_timeout_min'], self.cluster_config['election_timeout_max'])

        while (time.time()-self.last_time_heartbeat) < self.election_timeout:
                # time.sleep(self.election_timeout - (time.time()-self.last_time_heartbeat))
            if self.stop_election_timeout:
                return
            else:
                continue

        self.commit_log.dump_print(f"Node {self.node_id} election timer timed out, Starting election.")
        # print(f"Timeout occured on Raft Server node_id: {self.node_id} on role {self.state} on address: {self.ip}:{self.port}")
        
    def RequestVote(self, request: RequestVoteArgs, context):
        self.last_time_heartbeat = time.time()

        candidate_term = request.term
        candidate_id = request.candidateId
        candidate_last_log_index = request.lastLogIndex
        candidate_last_log_term = request.lastLogTerm

        if candidate_term > self.term:
            self.term = candidate_term
            self.voted_for = candidate_id

            if self.state == 'candidate':
                self.stop_election_timeout = True

            self.state = 'follower'

        last_index, last_term = self.commit_log.get_last_index_term()

        logOK = (candidate_last_log_term > last_term) or (candidate_last_log_term == last_term and candidate_last_log_index >= last_index)

        if candidate_term == self.term and logOK and (self.voted_for is None or self.voted_for == candidate_id):
            self.voted_for = candidate_id
            self.commit_log.dump_print(f"Vote granted for Node {candidate_id} in term {self.term}.")
            return RequestVoteReply(term=self.term, voteGranted=True, remainingLease=self.leader_lease_timeout) 
        else:
            self.commit_log.dump_print(f"Vote denied for Node {candidate_id} in term {self.term}.")
            return RequestVoteReply(term=self.term, voteGranted=False, remainingLease=self.leader_lease_timeout)
        
        
    def update_log(self, prev_log_index, leader_commit, entries):
        last_index, last_term = self.commit_log.get_last_index_term()

        if len(entries) > last_index + 1:
            self.commit_log.truncate()
            for entry in entries:
                command, term = entry.data, entry.term
                self.commit_log.log(term, command)

        # print(leader_commit, self.commit_index, "in update_log")
        if leader_commit > self.commit_index:
            commit = -1
            log_slice = self.commit_log.read_logs_start_end(self.commit_index+1)

            for log_entry in log_slice:
                command = log_entry.data
                term = log_entry.term

                if command != "NO-OP":
                    key, value = command.strip().split()[1:]
                    key = key.strip()
                    value = value.strip()
                    self.databasee[key] = value                
                    self.commit_log.dump_print(
                        f"Node {self.node_id} (follower) committed the entry <{command}> to the state machine."
                    )
                
                self.commit_index += 1
                
        self.commit_index = leader_commit
        return

    
    def AppendEntries(self, request: AppendEntriesArgs, context):
        self.last_time_heartbeat = time.time()
        
        term  = request.term
        leader_id = request.leaderId
        prev_log_index = request.prevLogIndex
        prev_log_term = request.prevLogTerm
        entries = request.entries
        leader_commit = request.leaderCommit
        self.leader_lease_timeout = request.leaseInterval
        self.start_timestamp_leader_lease = time.time()
        # print(self.leader_lease_timeout, "in AppendEntries")
        
        # print(term, leader_id, prev_log_index, prev_log_term,  entries, leader_commit, "in AppendEntries")
        # print(f"{leader_id}: {self.leader_id}")
        # print(f"{term}: {self.term}")
        # print(f"{leader_commit}, {self.commit_index}")
        # print(f"{prev_log_index}, {last_index}")
        # print(f"{prev_log_term}, {last_term}")
        # print(entries, "in AppendEntries")
        

        if term > self.term:
            self.term = term
            self.voted_for = None
            
            if self.state == 'candidate':
                self.stop_election_timeout = True

            self.state = 'follower'

        if term == self.term:
            self.leader_id = leader_id
            self.state = 'follower'

        last_index = self.commit_log.last_index
        log_at_prev_log_index = self.commit_log.read_logs_start_end(prev_log_index, prev_log_index)

        if len(log_at_prev_log_index) == 0:
            self_prev_term = 0
        else:
            self_prev_term = log_at_prev_log_index[0].term
    
        logOK = (last_index >= prev_log_index) and (prev_log_index == -1 or prev_log_term == self_prev_term) 

        # print(log_at_prev_log_index)
        # print(term == self.term, term, self.term)
        # print(last_index >= prev_log_index, last_index, prev_log_index)
        # print(prev_log_index == -1 or self_prev_term == prev_log_term, self_prev_term, prev_log_term)
        # print(logOK)
        
        if term == self.term and logOK:
            self.leader_id = leader_id  
            if len(entries) > prev_log_index + 1:
                self.commit_log.dump_print(f"Node {self.node_id} accepted AppendEntries RPC from {leader_id}.")

            self.update_log(prev_log_index, leader_commit, entries)
            return AppendEntriesReply(term=self.term, success=True)
        else:
            self.commit_log.dump_print(f"Node {self.node_id} rejected AppendEntries RPC from {leader_id}.")
            return AppendEntriesReply(term=self.term, success=False)

    def request_vote_from_candidate(self, channel):
        last_index, last_term = self.commit_log.get_last_index_term()

        with grpc.insecure_channel(channel) as channel:
            stub = RaftStub(channel)
            request_vote_args = RequestVoteArgs(
                term = self.term,
                candidateId = self.node_id,
                lastLogIndex = last_index,
                lastLogTerm = last_term
            )

            try:
                response: RequestVoteReply = stub.RequestVote(request_vote_args, timeout=self.election_timeout)
                old_leader_lease_time = response.remainingLease
                # print(self.term, response.term, response.voteGranted, "in request_vote_from_candidate")
                if self.term  < response.term:
                    self.stop_election_timeout = True
                    self.state = 'follower'
                    return (0, old_leader_lease_time)
                else:
                    if self.state == 'candidate' and response.term == self.term and response.voteGranted:
                        return (1, old_leader_lease_time)
                    else:
                        return (0, old_leader_lease_time)
                
            except grpc.RpcError as e:
                # print(e)
                return (0, 0)
    
    def request_vote(self):
        with ThreadPool(processes=len(self.cluster_config['peers'])) as pool:
            results = pool.map(self.request_vote_from_candidate, [f"{peer['host']}:{peer['port']}"for peer in self.cluster_config['peers'] if peer['id'] != self.node_id])

        # print(results)
        total_votes = 1
        for res in results:
            total_votes += res[0]
            self.leader_lease_timeout = max(self.leader_lease_timeout, res[1])
        self.start_timestamp_leader_lease = time.time()

        if self.state == 'candidate' and total_votes > len(self.cluster_config['peers'])/2:
            # print("Election Won")
            self.stop_election_timeout = True
            self.state = 'leader'
            # self.commit_log.dump_print(f"New Leader waiting for Old Leader Lease to timeout.")


    def check_no_winner(self):
        self.last_time_heartbeat = time.time()
        self.start_election_timeout()

    def start_candidate(self):
        self.term += 1
        self.voted_for = self.node_idii

        t2 = Thread(target=self.request_vote)
        t1 = Thread(target=self.check_no_winner)

        t1.start()
        t2.start()
        t1.join()
        t2.join()
        return

    def start_leader(self):
        t1 = Thread(target=self.start_leader_lease)
        t1.start()
        self.leader_function()
        t1.join()
        return

    def start_leader_lease(self):
        self.leader_lease_timeout = self.lease_interval
        # self.start_timestamp_leader_lease = time.time()
        while self.leader_lease_timeout > 0:
            time.sleep(0.1)

        self.commit_log.dump_print(F"Leader {self.node_id} lease renewal failed. Stepping Down.")
        self.state = 'follower'
        return

    def leader_function(self):
        self.leader_id = self.node_id        
        just_started = True

        while True:
            if self.state == 'leader':
            
                if just_started:
                    # add no opp
                    command, term = "NO-OP", self.term
                    self.commit_log.log(term, command)  # log the command
                    self.last_indices[self.node_id] = self.commit_log.last_index
                    just_started = False
                
                # try:
                #     command, key, value, context = self.read_queue.get_nowait(block=False)
                #     command_string = f"{command} {key} {value}"
                #     self.commit_log.log(self.term, command_string)
                # except Exception as e:
                #     pass

                # self.start_timestamp_leader_lease = time.time()

                self.commit_log.dump_print(f"Leader {self.leader_id} sending heartbeat & Renewing Lease")
                with ThreadPool(processes=len(self.cluster_config['peers'])) as pool:
                    results = pool.map(
                        self.send_heartbeat, 
                        [peer for peer in self.cluster_config['peers'] if peer['id'] != self.node_id]
                    )    

                # try:
                #     command, key, value, context = self.read_queue.get_nowait(block=False)
                #     command_string = f"{command} {key} {value}"
                #     self.commit_log.log(self.term, command_string)
                # except Exception as e:
                #     pass

                if self.state == 'leader' and sum(results)+1 > len(self.cluster_config['peers'])/2:
                    self.commit_entries()
                    self.leader_lease_timeout = self.lease_interval

                time.sleep(self.heartbeat_interval)

            else:
                break
        return


    def send_heartbeat(self, peer):
        node_id = peer['id']
        address = f"{peer['host']}:{peer['port']}"
        
        prev_idx = self.last_indices[node_id]
        log_slice, prev_term = self.commit_log.read_logs_start(prev_idx)
        # print(log_slice, prev_idx, prev_term, "in send_heartbeat")
        # print(log_slice, prev_idx, prev_term, "in send_heartbeat")
        try:
            with grpc.insecure_channel(address) as channel:
                stub = RaftStub(channel)
                append_entries_args = AppendEntriesArgs(
                    term = self.term,
                    leaderId = self.node_id,
                    prevLogIndex = prev_idx,
                    prevLogTerm=prev_term,
                    leaseInterval = self.lease_interval,
                    entries = log_slice,
                    leaderCommit=self.commit_index
                )

                response: AppendEntriesReply = stub.AppendEntries(append_entries_args)

                response_term = response.term
                success = response.success

                if self.term < response_term:
                    self.term = response_term
                    self.state = 'follower'
                    self.commit_log.dump_print(f"{self.node_id} Stepping down")
                    return 0
                
                elif self.state == 'leader' and self.term == response_term:
                    if success:
                        self.last_indices[node_id] = self.last_indices[self.node_id]
                        return 1
                    else:
                        self.last_indices[node_id] = max(-1, prev_idx-1)
                        return 0
                    
        except Exception as e:
            # print(e)
            self.commit_log.dump_print(f"Error occurred while sending RPC to Node {node_id}.")
            return 0


    def commit_entries(self):
        # commit the entries
        logs, _ = self.commit_log.read_logs_start(self.commit_index+1)
        commit = -1
        for log in logs:
            command = log.data

        
            if command != "NO-OP":
                key, value = command.strip().split()[1:]
                key = key.strip()
                value = value.strip()
                self.databasee[key] = value

            commit += 1 
            if commit > self.commit_index:
                self.commit_index = commit
                if command != "NO-OP":
                    self.commit_log.dump_print(f"Node {self.leader_id} (leader) committed the entry {command} to the state machine.")
                # print(f"Key: {key} set to value: {value} in node_id: {self.node_id} or channel: {self.channel}")
        

    def ServeClient(self, request: ServeClientArgs, context):
        # print("Client Request Received on node_id:", self.node_id, "or channel:", self.channel)
        if self.leader_id is None:
            return ServeClientReply(Success=False, LeaderID=self.leader_id, Data="Leader not found")

        elif self.leader_id == self.node_id:
            
            if not self.leader_lease_timeout:
                return ServeClientReply(Success=False, LeaderID=self.leader_id, Data="Leader Lease Timeout, Redirecting to Leader")

            self.commit_log.dump_print(f"Node {self.leader_id} (leader) received an {request.Request} request.")
            request_list = request.Request.strip().split()
            command = request_list[0]
            
            if command == 'SET':
                key, value = request_list[1], request_list[2]
                
                current_commit_index = self.commit_index
                command_string = f"{command} {key} {value}" 
                self.commit_log.log(self.term, command_string)
                self.last_indices[self.node_id] = self.commit_log.last_index

                time.sleep(2)
                if self.commit_index > current_commit_index:
                    return ServeClientReply(Success=True, LeaderID=self.leader_id, Data=f"Key: {key} set to value: {value}")
                else:
                    return ServeClientReply(Success=False, LeaderID=self.leader_id, Data=f"Rejected: Entry Logged, but not committed yet.")

            elif command == 'GET':
                key = request_list[1]
                if key in self.databasee:
                    return ServeClientReply(Success=True, LeaderID=self.leader_id, Data=f"Value: {self.databasee[key]}")
                else:
                    return ServeClientReply(Success=True, LeaderID=self.leader_id, Data=f"Key: {key} not found")
                
        else:
            return ServeClientReply(Success=False, LeaderID=self.leader_id, Data="Redirecting to Leader")
        
    def start_leader_lease_timeout(self):
        while True:
            while self.leader_lease_timeout > 0:
                self.leader_lease_timeout -= (time.time()-self.start_timestamp_leader_lease)
                self.start_timestamp_leader_lease = time.time()
                # time.sleep(0.1)

    def start(self):
        t1 = Thread(target=self.serve)
        t2 = Thread(target=self.start_leader_lease_timeout)
        
        try:
            t1.start()
            t2.start()
            time.sleep(0.1)
            self.assign_role()

        except KeyboardInterrupt: 
            print("Exiting...")
            self.server.stop(0)
            t1.join()
            t2.join()


        except Exception as e:
            print(e)
            print(f"Raft Server stopped with error: {e}")
            t1.join()
            t2.join()

        finally:
            t1.join()
            t2.join()
            self.commit_log.write_metadata(self.term, self.voted_for, self.commit_index)
            # self.commit_log.truncate_dump()
            self.commit_log.save_database(self.databasee)


    def run(self):
        self.start()
