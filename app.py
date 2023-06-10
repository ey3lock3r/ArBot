from exchange import OpenOcean_Exchange

import aiohttp
import asyncio
import pprint
import pandas as pd
pd.set_option('display.max_columns', None)

async def main():
    
    url = {
        'test': 'open-api.openocean.finance',
        'prod': 'open-api.openocean.finance'
    }
    oe_exch = OpenOcean_Exchange(url=url, env='test')
    tasks = []
    # tasks.append(asyncio.create_task(asyncio.sleep(10)))
    
    async with aiohttp.ClientSession() as sess:
        asyncio.gather(asyncio.create_task(oe_exch.getTokens(sess)))
        # await oe_exch.getTokens(sess)
        await oe_exch.getPriceData()
        await asyncio.sleep(10)
        print(pd.DataFrame(oe_exch.tokens.values()))
        print('end!')

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())