import ledger as ld
import pandas as pd
from coinbase.wallet.client import Client

class CoinbaseClient:
  def __init__(self, apiKey: str, apiSecret: str):
    self.apiKey = apiKey
    self.apiSecret = apiSecret
    self.client = Client(apiKey, apiSecret)

  def getAccountId(self, currency: str) -> str:
    accounts = []
    for account in self.client.get_accounts()["data"]:
      if account["currency"] == currency:  
         return account["id"]
    raise Exception("Currency not found on this exchange")
      
  def getLedgerForAsset(self, currency: str) -> ld.Ledger:   
    accountId = self.getAccountId(currency) 
    return self.getLedger(accountId)
      
  def getLedger(self, accountId: str) -> ld.Ledger:
    txnTimes = []
    quantities = []
    prices = []
    costBasis = []
    txnTypes = []
 
    txns = self.client.get_transactions(accountId, limit=100) 
    for txn in txns["data"]:
      if txn["type"].upper() == "ADVANCED_TRADE_FILL":    
          txnTypes.append("BUY")
          costBasis.append(float(txn["native_amount"]["amount"]))
          txnTimes.append(txn["created_at"])
          quantities.append(float(txn["amount"]["amount"])) 
          prices.append(float(txn["native_amount"]["amount"]) / float(txn["amount"]["amount"]))
      elif txn["type"].upper() == "INTEREST":
          txnTypes.append("INTEREST")  
          costBasis.append(0.0)
          txnTimes.append(txn["created_at"])
          quantities.append(float(txn["amount"]["amount"])) 
          prices.append(float(txn["native_amount"]["amount"]) / float(txn["amount"]["amount"]))

    buys = self.client.get_buys(accountId, limit=100) 
    for buy in buys["data"]:
      txnTypes.append("BUY")  
      costBasis.append(float(buy["total"]["amount"]))
      txnTimes.append(buy["created_at"])
      quantities.append(float(buy["amount"]["amount"]))
      prices.append(float(buy["subtotal"]["amount"]) / float(buy["amount"]["amount"]))

    sells = self.client.get_sells(accountId, limit=100) 
    for sell in sells["data"]:
      txnTypes.append("SELL")  
      costBasis.append(-float(sell["total"]["amount"]))
      txnTimes.append(sell["created_at"])
      quantities.append(-float(sell["amount"]["amount"]))
      prices.append(float(sell["subtotal"]["amount"]) / float(sell["amount"]["amount"]))
    
    data = { 
             "Transaction Time": txnTimes, 
             "Quantity": quantities, 
             "Purchase Price": prices, 
             "Cost": costBasis,
             "Type": txnTypes
           }

    ledger: ld.Ledger = pd.DataFrame(data)
    ledger["Transaction Time"] = pd.to_datetime(ledger["Transaction Time"])
    return ledger
