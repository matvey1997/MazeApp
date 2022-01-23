import argparse
import asyncio
import datetime as dt
import socket
import sys

INPUT_PREFIX = '> '


class ClientApp:
    is_logged_in: bool = False
    username: str

    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    async def communicate(self, message):
        self.writer.write(f'{message}\r\n'.encode())
        response = (await self.reader.read(1024)).decode()
        code = response.split()[0]
        return code, response

    async def register_loop(self, username, password):
        will = None
        while will not in ['y', 'n']:
            will = input('Unknown user, want to register? y/n: ').lower()

        if will.lower() == 'n':
            return

        code, response = await self.communicate(f'REGISTER {username} {password}')

        if code != '201':
            raise Exception(response)

        print('Registered successfully')
        self.is_logged_in = True
        self.username = username
        return

    async def auth_loop(self):
        while not self.is_logged_in:
            username = input('Username: ')
            password = input('Password: ')

            code, response = await self.communicate(f'CONNECT {username} {password}')

            if code == '200':
                print('Login successful!')
                self.is_logged_in = True
                self.username = username
                return
            if code == '403':
                print('Password mismatch, try again')
                continue
            if code != '402':
                print(f'Unexpected server response code: {response}')
                raise Exception(response)

            await self.register_loop(username, password)

    async def movement_loop(self, task_id):
        code, response = await self.communicate(f'MOVEMENT {task_id}')
        
        if code == '206':
            print('Unfortunatelly, there is a wall. Where should I go now?')
            return
        if code == '205':
            print('Congratulations!!! You have successfully escaped the MAZE!')
            self.escaped = True
            return
        if code == '200':
            print('You go a few steps in a choosen direction... Where to go now?')
            return

    async def logic_loop(self):
        await self.auth_loop()
        
        self.escaped = False
        print('- ' * 20)
        print(f'Welcome, {self.username}!')
        print('You are trapped in a maze, it is dark here so you can not see much. But you MUST find the way out...')
        print('- ' * 20)

        while True:
            if self.escaped == True:
                return
            print()
            print('0: Try to go Up')
            print()
            print('1: Try to go Right')
            print()
            print('2: Try to go Down')
            print()
            print('3: Try to go Left')

            choice = input(INPUT_PREFIX)
            if not choice.isnumeric() or int(choice) > 4:
                continue

            task_id = int(choice)
            await self.movement_loop(task_id)


async def main(host, port):
    print(F'Establishing connection with {host}:{port}...', end='')
    sys.stdout.flush()

    future = asyncio.wait_for(asyncio.open_connection(host, port), 10)
    try:
        reader, writer = await future
    except ConnectionRefusedError as exc:
        print(f' Error! Host "{host}" refusing connection on port {port}')
        return
    except socket.gaierror as exc:
        print(f' Error! Cannot resolve host "{host}"')
        return
    except asyncio.exceptions.TimeoutError:
        print(f' Error! Connection to "{host}:{port}" timed out')
        return

    print(' done!')

    app = ClientApp(reader, writer)
    await app.logic_loop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True, help='IP to bind to')
    parser.add_argument('--port', required=True, help='port to bind to')
    args = parser.parse_args()

    asyncio.run(main(args.host, args.port))
