import aiohttp
import asyncio
import socketio

import json
import time
import logging
import numpy as np
import pandas as pd
import pprint

from datetime import date, datetime, timedelta, timezone
from typing import Union, Optional, NoReturn
import websockets

from web3 import Web3
from web3.middleware import geth_poa_middleware

from exceptions import CBotResponseError , CBotError

class OpenOcean_Exchange:
    """The class describes the object of a simple bot that works with the Deribit exchange.
    Launch via the run method or asynchronously via start.
    The business logic of the bot itself is described in the worker method."""

    def __init__(self, url, env, chain='bsc', ver='v3', gasTran='instant', # standard, fast, instant
        base_token: str = 'BNB',
        logger: Union[logging.Logger, str, None] = None):

        self.url = url[env]
        # self.__credentials = auth[env]
        self.env = env
        self.chain = chain
        self.ver = ver
        self.gasTran = gasTran
        self.base_token = base_token

        self.logger = (logging.getLogger(logger) if isinstance(logger,str) else logger)

        if self.logger is None:
            self.logger = logging.getLogger(__name__)

        rpc = 'https://bsc-dataseed.binance.org/'
        web3 = Web3(Web3.HTTPProvider(rpc))
        web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.web3 = web3

        self.init_vals()
        self.logger.info(f'Bot init..')

    @property
    def keep_alive(self) -> bool :
        return self._keep_alive

    @keep_alive.setter
    def keep_alive(self, ka: bool):
        self._keep_alive = ka

    def init_vals(self):

        self.keep_alive = True
        self.gasPrice = 0.0
        self.tokens = {}
        self.ord_size = 4


    async def fetch(self, sess, url, params={}):

        async with sess.get(url, params=params) as resp:
            obj = await resp.json()
            self.logger.debug(f'Fetch ==> {obj}')

            return obj

    def get_response_result(self, obj,
                            raise_error: bool = True,
                            result_prop: str = 'data') -> Optional[dict]:
        """Receives the response body from the server, then returns an object
        located in result_prop, or throws an exception if from the server
        received error information
        """

        if obj['code'] == 200:
            if result_prop == 'full':
                return obj
            else:
                return obj[result_prop]

        else:
            self.keep_alive = False
            self.logger.debug('Error found!')
            self.logger.debug(f'Error: code: {obj["code"]}')
            self.logger.debug(f'Error: msg: {obj[result_prop]}')

            if raise_error:
                raise CBotResponseError(obj[result_prop],obj['code'])

            return None

    async def getTokens(self, sess) -> NoReturn:
        
        self.logger.info('get_tokens')

        url = f'https://{self.url}/{self.ver}/{self.chain}/tokenList'

        tokens = self.get_response_result(await self.fetch(sess, url))
        # self.base_token_dict = self.tokens.pop(self.base_token, None)
        tokens = pd.DataFrame(tokens)
        tokens.set_index('id', drop=False, inplace=True)
        self.tokens = tokens.to_dict('index')
        self.base_token_dict = self.tokens.pop(self.base_token, None)
        # print(pd.DataFrame(self.tokens))

    async def quote(self, sess, base, qt, amt):
        self.logger.info('quote')

        url = f'https://{self.url}/{self.ver}/{self.chain}/quote'

        parms = {
            'chain'          : self.chain,
            'inTokenAddress' : base,
            'outTokenAddress': qt,
            'amount'         : amt,
            'gasPrice'       : 5,
            'slippage'       : 1
        }

        return self.get_response_result(await self.fetch(sess, url, params=parms))

    async def init_quote(self, sess, key):
        # global tokens, base_token, base_token_dict
        print(f'init_quote {key}')

        amt = 4
        try:
            res = await self.quote(sess, self.base_token_dict['address'], self.tokens[key]['address'], amt)
            # convert outAmount to ether
            print(f"wei: {res['outAmount']}")
            amtFromWei = self.web3.fromWei(res['outAmount'], "ether")
            self.tokens[key]['amount'] = amtFromWei
            print(f"ether: {amtFromWei}")

        except Exception as E:
            print(f'key: {key} Error1: {E}')

    async def ret_quote(self, sess, key):
        # global tokens, base_token, base_token_dict
        print(f'ret_quote {key}')

        try:
            res = await self.quote(self.tokens[key]['address'], self.base_token_dict['address'], self.tokens[key]['amount'])
            amtFromWei = self.web3.fromWei(res['outAmount'], "ether")
            self.tokens[key]['ret_amount'] = amtFromWei

        except Exception as E:
            print(f'key: {key} Error2: {E}')

    async def getPriceData(self) -> NoReturn:
        self.logger.info('getPriceData')

        async with aiohttp.ClientSession() as session:
            try:
                # to be deleted
                # await self.getTokens(session)

                # while self.keep_alive:
                tasks = []
                for key in self.tokens:
                    tasks.append(asyncio.create_task(self.init_quote(session, key)))

                await asyncio.gather(*tasks)

                tasks = []
                for key in self.tokens:
                    tasks.append(asyncio.create_task(self.ret_quote(session, key)))

                await asyncio.gather(*tasks)
                   

                # pprint.pprint(pd.DataFrame(self.tokens).set_index('id'))

            except Exception as E:
                print(f'Error: {E}')

    async def getGasPrice(self) -> NoReturn:

        url = f'wss://{self.url}/socket'
        monitorID = ''

        async for websocket in websockets.connect(url):

            if monitorID:
                try:
                    await self.unsubscribe(websocket, monitorID)
                except Exception as E:
                    self.logger.info(f'Error during unsubscribe on getGasPrice: {E}')

            if not self.keep_alive:
                break

            await websocket.send((
                'getGasPrice', 
                { 'chain' : self.chain }
            ))

            while self.keep_alive:
                try:
                    message = self.get_response_result(await websocket.recv(), result_prop='full')
                    self.gasPrice = message['data'][self.gasTran]
                    self.logger.info(f'Gas price: {self.gasPrice}')
                    print(self.gasPrice)
                    # self.monitorIDs.add(message['params']['monitorId'])
                    
                except Exception as E:
                    # await asyncio.sleep(delay)
                    self.logger.info(f'Reconnecting listener for getGasPrice')
                    break

    async def ws_quote(self) -> NoReturn:

        url = f'wss://{self.url}/socket'
        monitorID = ''

        async for websocket in websockets.connect(self.url):

            if monitorID:
                try:
                    await self.unsubscribe(websocket, monitorID)
                except Exception as E:
                    self.logger.info(f'Error during unsubscribe on ws_quote: {E}')

            if not self.keep_alive:
                break

            # loop tokens:
            # 
            await websocket.send(
                'quote',
                { 'chain' : self.chain }
            )

            while self.keep_alive:
                try:
                    message = self.get_response_result(await websocket.recv(), result_prop='full')
                    

                    # self.monitorIDs.add(message['params']['monitorId'])
                    
                except Exception as E:
                    # await asyncio.sleep(delay)
                    self.logger.info(f'Reconnecting listener for ws_quote')
                    break

    async def unsubscribe_all(self, ws) -> Optional[dict]:
        self.logger.info('unsubscribe_all')

        await ws.send(
            self.create_message(
                'public/unsubscribe_all',
                {}
            )
        )

        return self.get_response_result(await ws.recv())

    async def grace_exit(self):
        self.logger.info('grace_exit')
        async with websockets.connect(self.url) as websocket:
            await self.unsubscribe_all(websocket)