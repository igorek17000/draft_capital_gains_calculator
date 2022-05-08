import coinbaseApi as cbApi
import json
import ledger as ld
import pandas as pd
import plotDistribution as pltD
from typing import List

if __name__ == '__main__':
#  ledger: ld.Ledger = pd.read_excel("../data/ADA.xlsx", index_col=None, header=0) 
  apiKey = ""
  apiSecret = ""
  with open("api.json") as f:
    cf = json.load(f) 
    apiKey = cf["Service Provider"]["Authn"]["Coinbase"]["Key"]
    apiSecret = cf["Service Provider"]["Authn"]["Coinbase"]["Secret"]

  distributions: List[pltD.Distribution] = []

  cb = cbApi.CoinbaseClient(apiKey, apiSecret)
  for asset in ["ADA", "BTC", "ETH"]:
    ledger = cb.getLedgerForAsset(asset)  
    report, inventory = ld.getCapitalGains(ledger=ledger)
    for r in report:
      print(str(r))
    _, dist = pltD.getDistribution(ledger=ledger)
    distributions.append((asset, dist))

  pltD.plotMultiDistribution(distributions)
