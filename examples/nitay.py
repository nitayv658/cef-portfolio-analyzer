import aiohttp, asyncio

async def fetch(url, session):
    async with session.get(url) as response:
        return await response.text()

async def main():
    urls = ['https://example.com', 'https://python.org', 'https://wix.com']
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(fetch(url, session) for url in urls))
        print(results)

asyncio.run(main())
