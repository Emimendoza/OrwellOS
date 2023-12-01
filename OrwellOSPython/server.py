import ssl
from dataclasses import dataclass

import websockets as ws
import sqlite3
import json
import asyncio


class Server:

    # Map of types to names
    typeMap = {
        0: 'Computer',
        1: 'Turtle',
        2: 'Advanced Computer',
        3: 'Advanced Turtle'
    }

    def __init__(self, host, port, dbPath):
        self.host = host
        self.port = port
        self.sql = sqlite3.connect(dbPath)
        self.clientCount = 0
        self.clients = []
        self.createTable()

    def createTable(self):
        cursor = self.sql.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS clients (computerID INTEGER PRIMARY KEY, osVersion TEXT, computerName TEXT, computerType INTEGER)')
        cursor.execute('CREATE TABLE IF NOT EXISTS blocks (x INTEGER, y INTEGER, z INTEGER, type TEXT, computerID INTEGER)')  # ComputerID is -1 for blocks that are not a computer or turtle
        cursor.execute('CREATE TABLE IF NOT EXISTS items (type TEXT, computerID INTEGER, count INTEGER)')  # This table keeps track of items in the possession of computers and turtles
        cursor.execute('CREATE TABLE IF NOT EXISTS zones (x INTEGER, y INTEGER, z INTEGER, widthI INTEGER, heightI INTEGER, depthI INTEGER, typeI INTEGER)')  # This table keeps track of zones
        self.sql.commit()

    async def run(self):
        async with ws.serve(self.handler, self.host, self.port, ssl=ssl.SSLContext()) as server:
            await server.wait_closed()

    @staticmethod
    async def getOrderJson(order: str, args: list | None = None):
        if args is None:
            args = []
        orderJson = {
            'order': order,
            'data': args
        }
        return json.dumps(orderJson)

    async def handler(self, websocket: ws.WebSocketServerProtocol):
        # Handshake with client
        currClient = self.clientCount
        self.clientCount += 1
        client = None
        try:
            await websocket.send('Hello')
            data = await websocket.recv()
            if data.startswith('Hello') and data.endswith('OrwellOS'):
                print(f'{currClient}:Connected to {data[6:]}')
            await websocket.send(await self.getOrderJson('identify'))
            data = await websocket.recv()
            # Parse JSON data
            data = json.loads(data)
            # Sterilize data
            data['computerID'] = int(data['computerID'])
            data['osVersion'] = str(data['osVersion'])
            data['computerName'] = str(data['computerName'])
            data['computerType'] = int(data['computerType'])

            # Check if client is already registered
            cursor = self.sql.cursor()
            cursor.execute('SELECT * FROM clients WHERE computerID=?', (data['computerID'],))
            clientData = cursor.fetchone()
            if clientData is None:
                # Register client
                cursor.execute('INSERT INTO clients VALUES (?,?,?,?)',
                               (data['computerID'], data['osVersion'], data['computerName'], data['computerType']))
                self.sql.commit()
                cursor.execute('SELECT * FROM clients WHERE computerID=?', (data['computerID'],))
                clientData = cursor.fetchone()
                print(f'{currClient}:Registered {data["computerName"]}. A new {self.typeMap[data["computerType"]]} joins the network')
            client = Client(currClient, clientData[0], clientData[1], clientData[2], clientData[3], websocket)
            self.clients.append(client)
            while True:
                data = await websocket.recv()
                print(data)
        except ws.ConnectionClosedError:
            print(f'{currClient}:Connection closed')
        except Exception as e:
            print(f'{currClient}:Error {e}')
        finally:
            if client is not None:
                self.clients.remove(client)
                print(f'{currClient}:Disconnected from {client.computerName}')
            else:
                print(f'{currClient}:Disconnected')

@dataclass
class Client:
    id: int
    computerID: int
    osVersion: str
    computerName: str
    computerType: int
    websocket: ws.WebSocketServerProtocol


@dataclass
class Block:
    x: int
    y: int
    z: int
    type: str
    computerID: int

@dataclass
class Item:
    type: str
    computerID: int
    count: int

@dataclass
class Zone:
    x: int
    y: int
    z: int
    width: int
    height: int
    depth: int
    type: int  # 0 is a mine, 1 is a base (no mining allowed), 3 is a safe zone (turtles inside cannot leave without permission), 4 is a no go zone (turtles are to avoid this zone at all costs)