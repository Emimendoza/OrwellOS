import ssl
from dataclasses import dataclass

import websockets as ws
import sqlite3
import json
from os import path
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
        if not path.exists(dbPath):
            open(dbPath, 'w').close()  # Create empty file to store database
        self.sql = sqlite3.connect(dbPath)
        self.clientCount = 0
        self.clients = []
        self.createTable()

    def createTable(self):
        cursor = self.sql.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS clients (computerID INTEGER PRIMARY KEY, osVersion TEXT, '
                       'computerName TEXT, computerType INTEGER)')
        cursor.execute('CREATE TABLE IF NOT EXISTS blocks (x INTEGER, y INTEGER, z INTEGER, typeT TEXT, computerID '
                       'INTEGER, PRIMARY KEY (x, y, z))')  # ComputerID is -1 for blocks that are not a computer or turtle
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS items (type TEXT, computerID INTEGER, count INTEGER)')  # This table keeps track of items in the possession of computers and turtles
        cursor.execute('CREATE TABLE IF NOT EXISTS zones (x INTEGER, y INTEGER, z INTEGER, widthI INTEGER, '
                       'heightI INTEGER, depthI INTEGER, typeI INTEGER, PRIMARY KEY(x, y, z))')  # This table keeps track of zones
        cursor.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, hashedPassword TEXT, salt TEXT)')
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
        user = None
        try:
            await websocket.send('Hello')
            data = await websocket.recv()
            if data.startswith('Hello') and data.endswith('OrwellOS'):
                print(f'{currClient}:Connected to {data[6:]}')
                # Pass computer request to computer handler
                client = await self.computerHandler(websocket, currClient)
            elif data.startswith('Login'):
                print(f'{currClient}:Login request from {data[6:]}')
                # Pass login request to user handler
                user = await self.userHandler(websocket, currClient)
            else:
                print(f'{currClient}:Invalid request')
        except ws.ConnectionClosedError:
            print(f'{currClient}:Connection closed')
        except Exception as e:
            print(f'{currClient}:Error {e}')
        finally:
            if client is not None:
                self.clients.remove(client)
                if client.websocket.open:
                    await client.websocket.close()
                print(f'{currClient}:Disconnected from {client.computerName}')
            elif user is not None:
                self.clients.remove(user)
                if user.websocket.open:
                    await user.websocket.close()
                print(f'{currClient}:Disconnected from {user.username}')
            else:
                print(f'{currClient}:Disconnected')

    async def userHandler(self, webs: ws.WebSocketServerProtocol, currClient: int):
        return User(currClient, '', '', '', webs)

    async def computerHandler(self, webs: ws.WebSocketServerProtocol, currClient: int):
        await webs.send(await self.getOrderJson('identify'))
        data = await webs.recv()
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
            print(
                f'{currClient}:Registered {data["computerName"]}. A new {self.typeMap[data["computerType"]]} joins '
                f'the network')
        client = Client(currClient, clientData[0], clientData[1], clientData[2], clientData[3], asyncio.Queue(), webs)
        self.clients.append(client)
        connected = True
        while connected:
            curr_order = await client.command_queue.get()
            await webs.send(curr_order)
            data = await webs.recv()
            data = json.loads(data)
            if data['order'] == 'disconnect':
                connected = False
            else:
                pass  # TODO: Handle orders
        return client



@dataclass
class User:
    id: int
    username: str
    hashedPassword: str
    salt: str
    websocket: ws.WebSocketServerProtocol


@dataclass
class Client:
    id: int
    computerID: int
    osVersion: str
    computerName: str
    computerType: int
    command_queue: asyncio.Queue
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
