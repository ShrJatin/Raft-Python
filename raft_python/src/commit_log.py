from datetime import datetime
from threading import Lock
import os, tqdm
from raft.raft_pb2 import *
import sys
from multiprocessing import Process


class CommitLog:
    def __init__(self, node_id=None, folder=None, file='logs.txt', dump_file='dump.txt', metadata_file='metadata.txt', database_file='database.txt'):
        if folder:
            self.file = f"{folder}/{file}" if node_id else f"{folder}/{file}"
            self.dump_file = f"{folder}/{dump_file}" if node_id else f"{folder}/{dump_file}"
            self.metadata_file = f"{folder}/{metadata_file}" if node_id else f"{folder}/{metadata_file}"
            self.database_file = f"{folder}/{database_file}" if node_id else f"{folder}/{database_file}"
        else:   
            self.file = file
            self.dump_file = dump_file
            self.metadata_file = metadata_file
            self.database_file = database_file
        
        # sys.stdout = open(self.dump_file, 'a')

        self.lock = Lock()
        self.lock_2 = Lock()
        self.create_files()
        self.last_term = 0
        self.last_index = len(self.read_log()) - 1
        # self.truncate()

    def create_files(self):

        if not os.path.exists(self.file):
            with self.lock:
                with open(self.file, 'w') as f:
                    f.truncate()
        
        if not os.path.exists(self.dump_file):
            with self.lock_2:
                with open(self.dump_file, 'w') as f:
                    f.truncate()
        
        if not os.path.exists(self.database_file):
            with self.lock:
                with open(self.database_file, 'w') as f:
                    f.truncate()

    def write_metadata(self, term, voted_for, commit_index):
        with self.lock:
            with open(self.metadata_file, 'w') as f:
                f.write(f"{term} {voted_for} {commit_index}")
    
    def read_metadata(self):
        try:
            with self.lock:
                with open(self.metadata_file, 'r') as f:
                    term, voted_for, commit_index = f.read().strip().split(" ")
                    return int(term), int(commit_index), int(voted_for)
        except:
            return 0, -1, None
    
    def save_database(self, db:dict):
        # db is a dictionary
        with self.lock:
            with open(self.database_file, 'w') as f:
                for key, value in db.items():
                    f.write(f"{key} {value}\n")

    def read_database(self):
        try:
            with self.lock:
                with open(self.database_file, 'r') as f:
                    db = {}
                    for line in f:
                        key, value = line.strip().split(" ")
                        db[key] = value
                    return db
        except:
            return {}

    def truncate(self):
        # Truncate file
        with self.lock:
            with open(self.file, 'w') as f:
                f.truncate()
        
        self.last_term = 0
        self.last_index = -1

    def truncate_dump(self):
        with self.lock_2:
            with open(self.dump_file, 'w') as f:
                f.truncate()

    def dump_print(self, msg):
        print(msg)

        with self.lock_2:
            with open(self.dump_file, 'a') as f:
                msg = f"{msg}\n"    
                f.write(msg)
            return
  
    def get_last_index_term(self):
        with self.lock:
            return self.last_index, self.last_term
        
    def log(self, term, command):
        # Append the term and command to file along with timestamp
        with self.lock:
            with open(self.file, 'a') as f:
                message = f"{command} {term}"
                f.write(f"{message}\n")
                self.last_term = term
                self.last_index += 1

            return self.last_index, self.last_term
                
    def log_replace(self, entries, start):
        # Replace or Append multiple commands starting at 'start' index line number in file
        index = 0
        i = 0
        with self.lock:
            with open(self.file, 'r+') as f:
                if len(entries) > 0:
                    while i < len(entries):
                        if index >= start:
                            entry = entries[i]
                            command = entry.data
                            term = entry.term
                            
                            i += 1
                            message = f"{command} {term}"
                            f.write(f"{message}\n")
                            
                            if index > self.last_index:
                                self.last_term = term
                                self.last_index = index
                        
                        index += 1
                    
                    # Truncate all lines coming after last command.
                    f.truncate()
        
            return self.last_index, self.last_term
    
    def read_log(self):
        # Return in memory array of term and command
        with self.lock:
            output = []
            with open(self.file, 'r') as f:
                for line in f:
                    log = line.strip().split(" ")
                    command = " ".join(log[:-1])
                    term = int(log[-1])
                    log_entry = LogEntry()
                    log_entry.term = term
                    log_entry.data = command
                    output += [log_entry]
            
            return output
        
    def read_logs_start_end(self, start, end=None):
        # Return in memory array of term and command between start and end indices
        with self.lock:
            output = []
            index = 0
            with open(self.file, 'r') as f:
                for line in f:
                    if index >= start:
                        log = line.strip().split(" ")
                        command = " ".join(log[:-1])
                        term = int(log[-1])

                        log_entry = LogEntry()
                        log_entry.term = term
                        log_entry.data = command

                        output += [log_entry]
                    
                    index += 1
                    if end and index > end:
                        break
            return output
        
    def read_logs_start(self, start=0):
        with self.lock:
            output = []
            st = 0
            index = 0
            prev_term = 0

            with open(self.file, 'r') as f:
                for line in f:
                    log = line.strip().split(" ")
                    command = " ".join(log[:-1])
                    term = int(log[-1])

                    log_entry = LogEntry()
                    log_entry.term = term
                    log_entry.data = command

                    output.append(log_entry)

                    
                    if index == start:                        
                        prev_term = term
                    
                    index += 1

            return output, prev_term
