import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

Ledger = pd.DataFrame

@dataclass(frozen=True)
class CapitalGainsReport:
  taxableEventDate      : str 
  amountSold            : float
  sellPrice             : float
  basisBeforeSell       : float 
  quantityBeforeSell    : float
  basisAfterSell        : float 
  quantityAfterSell     : float
  totalCapitalGains     : float
  shortTermCapitalGains : float
  longTermCapitalGains  : float

  def __str__(self) -> str:
    str = "Sell Transaction Time: {0}\n".format(self.taxableEventDate)
    str += "Quantity sold: {0}\n".format(self.amountSold)
    str += "Sell price: {0}\n".format(self.sellPrice)
    str += "Quantity before sell: {0}\n".format(self.quantityBeforeSell)
    str += "Cost basis before sell: {0}\n".format(self.basisBeforeSell)
    str += "Quantity after sell: {0}\n".format(self.quantityAfterSell)
    str += "Cost basis after sell: {0}\n".format(self.basisAfterSell)
    str += "Capital gain on this transaction {0}\n".format(self.totalCapitalGains)
    str += "Long term gain + Short term gain = {0} + {1}\n".format(self.longTermCapitalGains, self.shortTermCapitalGains)
    return str

Inventory = pd.DataFrame

def liquidate(ledger: Ledger, price: float) -> Tuple[List[CapitalGainsReport], Inventory]:
  report, inventory = getCapitalGains(ledger)
  currentQuantity = -inventory["Quantity"].sum()
  if currentQuantity != 0:
    cost = -price * abs(currentQuantity)
    test = { 
             "Transaction Time": datetime.now(),
             "Quantity": currentQuantity,
             "Purchase Price": price,
             "Cost": cost,
             "Type": "SELL"
           } 
    inventory = inventory.append(test, ignore_index=True)
    liquidated, empty = getCapitalGains(inventory)
    report.append(liquidated[0]) 
  return report, empty
  
def sell(ledger: Ledger, quantity: float, price: float) -> Tuple[List[CapitalGainsReport], Inventory]:
  report, inventory = getCapitalGains(ledger)
  currentQuantity = inventory["Quantity"].sum()
  if quantity <= 0 or quantity > currentQuantity:
    raise Exception("Invalid quantity: should be greater than zero but no bigger than the current inventory") 

  cost = -price * abs(quantity)
  test = { 
           "Transaction Time": datetime.now(),
           "Quantity": -quantity,
           "Purchase Price": price,
           "Cost": cost,
           "Type": "SELL"
         } 
  inventory = inventory.append(test, ignore_index=True)
  sold, latest = getCapitalGains(inventory)
  report.append(sold[0]) 
  return report, latest
  
def getCapitalGains(ledger: Ledger) -> Tuple[List[CapitalGainsReport], Inventory]:
  report = []
  sortedByTime = ledger.sort_values(by="Transaction Time", ascending=True)
  sortedByTime.reset_index(drop=True, inplace=True)

  sellPts = []
  for idx, row in sortedByTime.iterrows():
    if row["Type"] == "SELL":
      sellPts.append(idx)

  for p in sellPts:
    amountSold = abs(sortedByTime.loc[p]["Quantity"])
    sellPrice = abs(sortedByTime.loc[p]["Purchase Price"])
    sellValue = abs(sortedByTime.loc[p]["Cost"])
    whenSold = sortedByTime.loc[p]["Transaction Time"]
    assets = sortedByTime.loc[0 : p]
    assets = assets[assets.Type != "SELL"]
    sortedByHIFO = assets.sort_values(by=["Purchase Price", "Transaction Time"], 
                                      ascending=[False, True])
    sortedByHIFO.reset_index(drop=True, inplace=True)

    qBefore = sortedByHIFO["Quantity"].to_numpy().sum()
    cBefore = sortedByHIFO["Cost"].to_numpy().sum()
    shortTermQuantitySold = 0.0
    longTermQuantitySold = 0.0

    for idx, row in sortedByHIFO.iterrows():
      if row["Quantity"] == 0.0:
        continue

      if amountSold >= row["Quantity"]:
        sortedByHIFO.loc[idx, "Quantity"] = 0.0
        sortedByHIFO.loc[idx, "Cost"] = 0.0
        amountSold = amountSold - row["Quantity"]

        if (whenSold - row["Transaction Time"]).days > 365:
          longTermQuantitySold += row["Quantity"]
        else:
          shortTermQuantitySold += row["Quantity"]
   
      else:
        sortedByHIFO.loc[idx, "Quantity"] = row["Quantity"] - amountSold
        fraction = sortedByHIFO.loc[idx, "Quantity"] / row["Quantity"]
        sortedByHIFO.loc[idx, "Cost"] = fraction * row["Cost"]

        if (whenSold - row["Transaction Time"]).days > 365:
          longTermQuantitySold += amountSold
        else:
          shortTermQuantitySold += amountSold

        amountSold = 0
        break

    qAfter = sortedByHIFO["Quantity"].to_numpy().sum()
    cAfter = sortedByHIFO["Cost"].to_numpy().sum()
    totalCapitalGains = sellValue - (cBefore - cAfter)
    longTermCapitalGains = longTermQuantitySold / (qBefore - qAfter) * totalCapitalGains
    shortTermCapitalGains = shortTermQuantitySold / (qBefore - qAfter) * totalCapitalGains

    temp = pd.merge(
             sortedByTime, 
             sortedByHIFO,  
             how="right", 
             left_on=["Transaction Time"], 
             right_on=["Transaction Time"],
             suffixes=("_left", None))

    temp.drop(["Quantity_left", "Cost_left", "Purchase Price_left", "Type_left"], 
             axis=1, inplace=True)

    sortedByTime = pd.concat([temp, sortedByTime.loc[p:]], axis = 0, sort = False) 

    r = CapitalGainsReport(taxableEventDate=whenSold,
                           amountSold=qBefore-qAfter,
                           sellPrice=sellPrice,
                           basisBeforeSell=cBefore,
                           quantityBeforeSell=qBefore, 
                           basisAfterSell=cAfter,
                           quantityAfterSell=qAfter,
                           totalCapitalGains=totalCapitalGains,
                           longTermCapitalGains=longTermCapitalGains,
                           shortTermCapitalGains=shortTermCapitalGains
                           )
    report.append(r)

  return report, sortedByTime[sortedByTime.Type != "SELL"]