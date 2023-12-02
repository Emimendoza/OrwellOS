
import OrwellOSPython as orwell
import asyncio
from os import path

db_path = "secrets/db.sqlite"
ssl_cert_path = "secrets/cert.pem"
ssl_key_path = "secrets/key.pem"
host = "localhost"
port = 28080


async def main(use_ssl: bool = True):
    if use_ssl:
        print("Using SSL")
        # Create self-signed certificate if it does not exist
        if not path.exists(ssl_cert_path) or not path.exists(ssl_key_path):
            orwell.create_self_signed_cert(ssl_cert_path, ssl_key_path)
            print(f'Created self-signed certificate at {ssl_cert_path} and {ssl_key_path}')
        else:
            print(f'Using certificate at {ssl_cert_path} and {ssl_key_path}')
    else:
        print("Not using SSL")
    ssl_cert = ssl_cert_path if use_ssl else None
    ssl_key = ssl_key_path if use_ssl else None

    server = orwell.Server(host, port, db_path, ssl_cert, ssl_key)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main(False))
