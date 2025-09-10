# quick local test: import device_parts function and call it directly
import asyncio
from app.main import device_parts

async def run():
    try:
        res = await device_parts('10250', month=['2025-09'])
        for r in res[:20]:
            print(r)
    except Exception as e:
        print('ERROR:', e)

if __name__ == '__main__':
    asyncio.run(run())
