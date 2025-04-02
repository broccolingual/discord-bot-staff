import os

TOKEN = os.environ.get('TOKEN')

MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_TCP_PORT = os.environ.get('MYSQL_TCP_PORT')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE')

DB_DSN = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@mysql:{MYSQL_TCP_PORT}/{MYSQL_DATABASE}"
