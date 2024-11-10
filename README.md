# BitTorrent Simulator

## Overview

This project aims to simulate the BitTorrent Protocol and a Peer-to-Peer (P2P) network architecture using Python and PyQt5. The client provides functionality to facilitate direct data exchange between multiple peers, thereby decentralizing file sharing without the need for a central server.

## Tools and Libraries Used

- **Python**: The primary programming language used for implementing BitTorrent protocol logic and peer-to-peer network functions.
- **PyQt5**: A Python library for developing a cross-platform graphical user interface (GUI). It is used to create an intuitive and user-friendly interface for interacting with the torrent client.
- **bencode.py:**: This module is often used in torrent applications to encode and decode `.torrent` files, which use bencoding (a special encoding format) to store metadata.
- **asyncio**: Enables asynchronous operations, allowing for simultaneous connections with multiple peers, enhancing download efficiency.

## Prerequisites

- Python 3.8+
- `pyqt5` for the GUI
- `requests` for handling tracker communications





## Setup

1. **Clone the Repository**
```
git clone https://github.com/Nandu-25/BitTorrent_Simulator.git
cd BitTorrent-simulator
```
2. **Install Dependencies**
```
python3 -m pip install PyQt5
python3 -m pip install -r requirements.txt
```

## Usage
1. To start the GUI, run the `torrent_gui.py` file 
```
python3 torrent_gui.py
```
2. Next, to download the file, click on the add icon and input your torrent file (/path)
3. To seed, go to the seed tab and input your file path
4. All the other icons like pause, resume and delete are quite intuitive and works while the file is downloading or seeding.

