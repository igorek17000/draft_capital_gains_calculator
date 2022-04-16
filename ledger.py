import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
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

Distribution = pd.DataFrame

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
  
def getMaximum(ledger: Ledger) -> Tuple[Inventory, float]:
  _, inventory = getCapitalGains(ledger)
  inventory = inventory[inventory.Quantity > 0]
  return inventory, inventory["Purchase Price"].max()
  
def getPercentiles(ledger: Ledger) -> Tuple[Inventory, float, List[float]]:
  inventory, highest = getMaximum(ledger)
  percentiles = []
  for i in range(11):
    percentile = highest - (0.10 * i * highest)
    percentiles.append(percentile)
  return inventory, highest, percentiles

def getDistribution(ledger: Ledger) -> Tuple[float, Distribution]:
  inventory, highest, bins = getPercentiles(ledger)
  def setBin(row) -> str:
    for i in range(len(bins)):
      if row["Purchase Price"] <= bins[i] and row["Purchase Price"] > bins[i + 1]:
        low =  "${:,.2f}".format(bins[i + 1])
        high = "${:,.2f}".format(bins[i])
        return "\$" + low + " - " + high
      if i == 8:
        break
  inventory["Percentile"] = inventory.apply(lambda row: setBin(row), axis=1)
  return highest, inventory

def plotDistribution(highest: float, dist: Distribution) -> None:
  dist = dist.groupby(["Percentile"])["Quantity"].sum().reset_index()  
  palette_color = sns.color_palette('bright')
  plt.pie(dist["Quantity"], labels=dist["Percentile"], colors=palette_color, autopct='%.0f%%')
  plt.suptitle("Percentage of ADA tokens by Price Range")
  plt.show()

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

    sortedByTime = pd.concat([temp, sortedByTime[p:]], axis = 0, sort = False) 

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

FUNCTIONS = {
  "liquidate": liquidate,
  "sell": sell,
  "getCapitalGains": getCapitalGains,
  "plotDistribution": plotDistribution
}

if __name__ == '__main__':
  ledger = pd.read_excel("../data/ADA.xlsx", index_col=None, header=0) 
  ledger["Transaction Time"] = pd.to_datetime(ledger["Transaction Time"])

  #f = FUNCTIONS["getCapitalGains"]

  #report, inventory = f(ledger=ledger)
  #currentQuantity = inventory["Quantity"].sum()
  #for r in report:
  #  print(str(r))
  #print("Current Inventory")
  #print(inventory)  
  #print("Current Quantity: {0}".format(currentQuantity))

  highest, dist = getDistribution(ledger)
  print(dist)
  plotDistribution(highest, dist)
