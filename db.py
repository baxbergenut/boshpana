import asyncpg
from config import config

async def create_pool():
    return await asyncpg.create_pool(
        host=config.DB_HOST,
        port=config.DB_PORT,
        database=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD
    )

def get_user(id):
    print(id)
def create_user(id):
    print(id)