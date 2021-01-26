import urllib.request
import json
import aiohttp
import os
import asyncio

async def test_post(endpoint):
    full_url = os.path.join(endpoint,'students')
    param = {'name':'John'}
    async with session.post(full_url, params=param) as resp:
        print(resp.text())

    return resp

async def get_problems(endpoint_test):
    session = aiohttp.ClientSession()
    return await session.get(endpoint_test)
    

api_ep = 'https://ujiyan-web-app.azurewebsites.net/'
api_problems = 'https://ujiyan-web-app.azurewebsites.net/tests/EC2A5FB5'


async def main():
    resp = await get_problems(api_problems)
    print(resp.status)
    json_data = await resp.json()
    print(json_data)
    print(json_data['title'])
    print(len(json_data['problems']))

# endopoint = ['students']

# params = {'name':'test'}

# req = urllib.request.Request(os.path.join(api_ep, endopoint[0]))

# with urllib.request.urlopen(req, params=params) as resp:
#     body = resp.read()

if __name__ == "__main__":
    asyncio.run(main())