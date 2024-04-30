# Raft implementation in Python using gRPC
This is a standalone implementation of Raft, incorporating Leader lease functionality for faster, serializable reads. The timers for heartbeat, leader lease and election are handled in real-time using threads, and communication between servers and clients is handled using gRPC.
