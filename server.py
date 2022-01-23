import argparse
import asyncio
import datetime as dt
import sqlite3
import typing as tp
import random
import uuid

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 8888


def gen_maze():
    x = 5
    y = 5
    res = ['#####','#...#','#.#.#','#A#.$','#####']
    for s in res:
        print(s)
        print()
    return res


class ServerAppException(Exception):
    response = '500'

    def __init__(self):
        super().__init__()


class ServerAppBadRequest(ServerAppException):
    response = '400'


class ServerAppNoLogin(ServerAppException):
    response = '401'


class ServerAppNotRegistered(ServerAppException):
    response = '402'


class ServerAppBadCredentials(ServerAppException):
    response = '403'


class ServerAppNotFound(ServerAppException):
    response = '404'


class ServerAppNotAllowed(ServerAppException):
    response = '405'


class ServerAppUnsupportedCommand(ServerAppException):
    response = '501'


class ServerContext:
    user: tp.Optional[str] = None
    is_authorized: bool = False


DDL2 = '''
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL
);
'''


class ServerApp:
    def __init__(self):
        self.connection = sqlite3.connect('server.sqlite')

        # checking tables
        c = self.connection.cursor()
        c.execute(DDL2)
        self.connection.commit()
        print('Created connection to user DB')

    def __del__(self):
        print('Closing connection to user DB')
        self.connection.commit()
        self.connection.close()

    def _handle_register(self, args: tp.List[str],
                         context: ServerContext) -> tp.Tuple[str, ServerContext]:
        if len(args) != 2:
            raise ServerAppBadRequest()

        try:
            cursor = self.connection.cursor()
            cursor.execute('INSERT INTO users VALUES (?, ?);', args)
            self.connection.commit()
        except sqlite3.Error:
            raise ServerAppNotAllowed()

        context.user = args[0]
        context.is_authorized = True
        self.maze = gen_maze()
        self.cur_x = 2
        self.cur_y = 1
        return f'201', context

    def _handle_connect(self, args: tp.List[str],
                        context: ServerContext) -> tp.Tuple[str, ServerContext]:
        if len(args) != 2:
            raise ServerAppBadRequest()

        print(args)

        cursor = self.connection.cursor()
        cursor.execute('SELECT password FROM users WHERE username = ?;', [args[0]])
        res = cursor.fetchone()

        if not res:
            raise ServerAppNotRegistered()

        if res[0] != args[1]:
            raise ServerAppBadCredentials()

        context.user = args[0]
        context.is_authorized = True
        self.maze = gen_maze()
        self.cur_x = 2
        self.cur_y = 1
        return '200', context

    def _handle_movement(self, args: tp.List[str],
                        context: ServerContext) -> tp.Tuple[str, ServerContext]:
        if not context.is_authorized:
            raise ServerAppNoLogin()

        direction = int(args[0])
        mv_x = 0
        mv_y = 0
        if direction == 0:
            print('Trying to go Up')
            print()
            mv_x = -1
        elif direction == 1:
            print('Trying to go Right')
            print()
            mv_y = 1
        elif direction == 2:
            print('Trying to go Down')
            print()
            mv_x = 1
        elif direction == 3:
            print('Trying to go Left')
            print()
            mv_y = -1
        new_x = self.cur_x + mv_x
        new_y = self.cur_y + mv_y
        if self.maze[new_x][new_y] == '#':
            print('Dead end')
            return '206', context
        elif self.maze[new_x][new_y] == '$':
            print('Escaped')
            return f'205', context
        self.cur_x = new_x
        self.cur_y = new_y
        print(f'Movement. Current position: {new_x}, {new_y}')
        return f'200', context

    _HANDLERS = {
        'REGISTER': _handle_register,
        'CONNECT': _handle_connect,
        'MOVEMENT': _handle_movement,
    }

    async def handle_connection(self, reader, writer):
        context = ServerContext()

        while True:
            data = await reader.read(1024)
            if not data:
                break

            try:
                message = data.decode().strip()
                addr = writer.get_extra_info('peername')
                print(f"[{addr!r}] {message!r}")
                args = message.split()

                handler = self._HANDLERS.get(args[0])
                if not handler:
                    raise ServerAppUnsupportedCommand()
                response_message, context = handler(self, args[1:], context)
                await asyncio.sleep(0.1)
            except ServerAppException as exc:
                response_message = exc.response
            except Exception as exc:
                print(f'ERR: {exc} {exc!r}')
                response_message = ServerAppException.response

            print(f"[{context.user if context.is_authorized else addr!r}]",
                  f"respond: {response_message!r}")
            writer.write(response_message.encode() + b'\r\n')
            await writer.drain()

        print("Close the connection")
        writer.close()


async def main(host, port):
    app = ServerApp()
    server = await asyncio.start_server(app.handle_connection, host, port)

    addr = server.sockets[0].getsockname()
    print(f'Serving on {addr}')

    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', help='IP to bind to')
    parser.add_argument('--port', help='port to bind to')
    args = parser.parse_args()

    try:
        asyncio.run(main(args.host or SERVER_HOST, args.port or SERVER_PORT))
    except KeyboardInterrupt:
        pass
