import os

TOKEN = os.environ.get('TOKEN')

MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
MYSQL_TCP_PORT = os.environ.get('MYSQL_TCP_PORT')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE')
DB_DSN = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@mysql:{MYSQL_TCP_PORT}/{MYSQL_DATABASE}"

SUPABASE_DB_DSN = f"postgresql+asyncpg://{os.environ.get('SUPABASE_DB_USER')}:{os.environ.get('SUPABASE_DB_PASSWORD')}@{os.environ.get('SUPABASE_DB_HOST')}:{os.environ.get("SUPABASE_DB_PORT")}/{os.envirion.get("SUPABASE_DB_NAME")}"
SUPABASE_API_URL = os.environ.get('SUPABASE_API_URL')
SUPABASE_API_KEY = os.environ.get('SUPABASE_API_KEY')
