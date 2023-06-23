from web3 import Web3
from web3.middleware import geth_poa_middleware

rpclist = ['https://bsc-dataseed1.binance.org/'
,'https://bsc-dataseed2.binance.org/'
,'https://bsc-dataseed3.binance.org/'
,'https://bsc-dataseed4.binance.org/'
,'https://bsc-dataseed1.defibit.io/'
,'https://bsc-dataseed2.defibit.io/'
,'https://bsc-dataseed3.defibit.io/'
,'https://bsc-dataseed4.defibit.io/'
,'https://bsc-dataseed1.ninicoin.io/'
,'https://bsc-dataseed2.ninicoin.io/'
,'https://bsc-dataseed3.ninicoin.io/'
,'https://bsc-dataseed4.ninicoin.io/']

class Web3_Wrapper():
    
    def __init__(self, rpc_list=[], pkey=''):

        self.__web3 = self.build_web3(rpc_list, pkey)
        self.web3 = self.__web3.copy()

    def build_web3(self, rpc, pkey):

        temp_list = []
        for url in rpc:
            web3 = Web3(Web3.HTTPProvider(rpc))
            web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            temp_list.append(web3)

        return temp_list