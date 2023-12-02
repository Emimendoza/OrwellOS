import OrwellOSPython as orwell

db_path = "secrets/db.sqlite"
host = "localhost"
port = 8080


def main():
    server = orwell.Server(host, port, db_path)


if __name__ == "__main__":
    main()
