import asyncio
import struct
import random
import time
import socket
from collections import defaultdict


class TrackerStorage:
    def __init__(self):
        self.connection_ids = {}
        self.transaction_ids = defaultdict(list)

    def add_connection_id(self, connection_id: int, expiration_duration: int = 300):
        expiration_time = time.time() + expiration_duration
        self.connection_ids[connection_id] = expiration_time

    def remove_connection_id(self, connection_id: int):
        if connection_id in self.connection_ids:
            del self.connection_ids[connection_id]

    def is_connection_id_valid(self, connection_id: int) -> bool:
        current_time = time.time()
        return connection_id in self.connection_ids and self.connection_ids[connection_id] > current_time

    def add_transaction_id(self, peer_id: bytes, transaction_id: int):
        self.transaction_ids[peer_id].append(transaction_id)

    def remove_transaction_id(self, peer_id: bytes, transaction_id: int):
        if peer_id in self.transaction_ids:
            self.transaction_ids[peer_id].remove(transaction_id)

    def get_transaction_ids(self, peer_id: bytes) -> list:
        return self.transaction_ids.get(peer_id, [])

    def clean_expired_connection_ids(self):
        current_time = time.time()
        expired_ids = [cid for cid, exp_time in self.connection_ids.items() if exp_time <= current_time]
        for cid in expired_ids:
            self.remove_connection_id(cid)


class TorrentData:
    def __init__(self, info_hash: bytes):
        self.info_hash = info_hash
        self.peers = {}
        self.seeders_count = 0
        self.leechers_count = 0
        self.interval = 1800 

    def add_peer(self, peer_id: bytes, peer_info: dict, is_seeder: bool = False):
        existing_peer = None
        for pid, info in self.peers.items():
            if info['ip'] == peer_info['ip'] and info['port'] == peer_info['port']:
                existing_peer = pid
                break
        if existing_peer:
            if self.peers[existing_peer]['is_seeder'] and not is_seeder:
                self.seeders_count -= 1
                self.leechers_count += 1
            elif not self.peers[existing_peer]['is_seeder'] and is_seeder:
                self.leechers_count -= 1
                self.seeders_count += 1
            self.peers[existing_peer] = peer_info
            self.peers[existing_peer]['is_seeder'] = is_seeder
        else:
            self.peers[peer_id] = peer_info
            self.peers[peer_id]['is_seeder'] = is_seeder
            if is_seeder:
                self.seeders_count += 1
            else:
                self.leechers_count += 1


    def remove_peer(self, peer_id: bytes):
        if peer_id in self.peers:
            if self.peers[peer_id]['is_seeder']:
                self.seeders_count -= 1
            else:
                self.leechers_count -= 1
            del self.peers[peer_id]

    def update_peer_counts(self):
        self.seeders_count = sum(1 for peer in self.peers.values() if peer['is_seeder'])
        self.leechers_count = len(self.peers) - self.seeders_count

    def complete_download(self, peer_id: bytes):
        if peer_id in self.peers and not self.peers[peer_id]['is_seeder']:
            self.peers[peer_id]['is_seeder'] = True
            self.leechers_count -= 1
            self.seeders_count += 1


class UDPTrackerServerProtocol:
    MAGIC_CONNECTION_ID = 0x41727101980

    def __init__(self):
        self.storage = TrackerStorage()
        self.torrents = {}

    def connection_made(self, transport):
        self.transport = transport
        print('Tracker server is running and waiting for connections...')

    def datagram_received(self, data, addr):
        print(f"Received {len(data)} bytes from {addr}")
        try:
            action, transaction_id = struct.unpack_from('!II', data, 8)
            if action == 0:
                print("announce")
                print(f"request : {data}")
                self.handle_connect(transaction_id, addr)
            elif action == 1:
                print("connect")
                print(f"request : {data}")
                self.handle_announce(data, transaction_id, addr)
        except Exception as e:
            print("error")
            print(data)
            print(f"Failed to process data: {e}")

    def handle_connect(self, transaction_id, addr):
        print(f"Handling connect request from {addr}")
        connection_id = random.randint(0, 2**64 - 1)
        self.storage.add_connection_id(connection_id)
        response = struct.pack('!IIQ', 0, transaction_id, connection_id)
        self.transport.sendto(response, addr)

    def handle_announce(self, data, transaction_id, addr):
        print(f"Handling announce request from {addr}")
        unpacked_data = struct.unpack_from('!QII20s20sQQQIIIIH', data)
        connection_id = unpacked_data[0]
        # action = unpacked_data[1]
        # transaction_id = unpacked_data[2]
        info_hash = unpacked_data[3]
        peer_id = unpacked_data[4]
        downloaded = unpacked_data[5]
        left = unpacked_data[6]
        uploaded = unpacked_data[7]
        event = unpacked_data[8]
        ip = unpacked_data[9]
        # key = unpacked_data[10]
        num_want = unpacked_data[11]
        port = unpacked_data[12]
        if not self.storage.is_connection_id_valid(connection_id):
            print(f"Invalid connection ID from {addr}")
            return
        if event == 3:
            if info_hash not in self.torrents:
                self.torrents[info_hash] = TorrentData(info_hash)
            is_seeder = left == 0
            self.torrents[info_hash].add_peer(peer_id, {'ip': addr[0], 'port': port}, is_seeder)
            leechers = self.torrents[info_hash].leechers_count
            seeders = self.torrents[info_hash].seeders_count
            response = struct.pack('!III', 1, transaction_id, self.torrents[info_hash].interval)
            response += struct.pack('!II', leechers, seeders)
            print(f"response : {response}")
            self.transport.sendto(response, addr)
        else:
            if info_hash not in self.torrents:
                self.torrents[info_hash] = TorrentData(info_hash)
            is_seeder = left == 0
            self.torrents[info_hash].add_peer(peer_id, {'ip': addr[0], 'port': port}, is_seeder)
            leechers = self.torrents[info_hash].leechers_count
            seeders = self.torrents[info_hash].seeders_count
            response = struct.pack('!III', 1, transaction_id, self.torrents[info_hash].interval)
            response += struct.pack('!II', leechers, seeders)
            # print(response)
            peer_list = b""
            peers = list(self.torrents[info_hash].peers.values())
            if num_want == -1:
                num_to_send = min(200, len(peers))
            else:
                num_to_send = min(num_want, len(peers))
            selected_peers = peers[:num_to_send]
            for peer in selected_peers:
                ip = peer['ip']
                peer_port = peer['port']
                try:
                    if ':' in ip:
                        ip_bytes = socket.inet_pton(socket.AF_INET6, ip)
                    else:
                        ip_bytes = socket.inet_aton(ip)
                    peer_list += struct.pack('!4sH', ip_bytes[:4], peer_port)
                except Exception as e:
                    print(f"Failed to process IP {ip} due to: {e}")
            response += peer_list
            print(f"response : {response}")
            self.transport.sendto(response, addr)

    # def get_peer_list(self, info_hash: bytes) -> bytes:
    #     peer_data = bytearray()
    #     for peer_id, peer_info in self.torrents[info_hash].peers.items():
    #         packed_peer = struct.pack('!4sH', bytes(map(int, peer_info['ip'].split('.'))), peer_info['port'])
    #         peer_data.extend(packed_peer)
    #     return peer_data


async def main():
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPTrackerServerProtocol(),
        local_addr=('localhost', 6881)
    )
    try:
        print("Tracker server is running...")
        await asyncio.sleep(3600)
    finally:
        transport.close()


if __name__ == "__main__":
    asyncio.run(main())
