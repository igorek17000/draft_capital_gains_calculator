import ledger as ld
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from typing import List, Tuple

Distribution = pd.DataFrame

def getMaximum(ledger: ld.Ledger) -> Tuple[ld.Inventory, float]:
  _, inventory = ld.getCapitalGains(ledger)
  inventory = inventory[inventory.Quantity > 0]
  return inventory, inventory["Purchase Price"].max()
  
def getPercentiles(ledger: ld.Ledger) -> Tuple[ld.Inventory, float, List[float]]:
  inventory, highest = getMaximum(ledger)
  percentiles = []
  for i in range(11):
    percentile = highest - (0.10 * i * highest)
    percentiles.append(percentile)
  return inventory, highest, percentiles

def getDistribution(ledger: ld.Ledger) -> Tuple[float, Distribution]:
  inventory, highest, bins = getPercentiles(ledger)
  def setBin(row) -> str:
    for i in range(len(bins)):
      if row["Purchase Price"] <= bins[i] and row["Purchase Price"] > bins[i + 1]:
        low =  str(round(bins[i + 1], 2))
        high = str(round(bins[i], 2))
        return "$" + low + " - " + high
      if i == 8:
        break
  inventory["Percentile"] = inventory.apply(lambda row: setBin(row), axis=1)
  return highest, inventory

def plotDistribution(distribution: Distribution) -> None:
  dist = distribution.groupby(["Percentile"])["Quantity"].sum().reset_index()  
  palette_color = sns.color_palette('bright')
  plt.pie(dist["Quantity"], labels=dist["Percentile"], colors=palette_color, autopct='%.0f%%')
  plt.suptitle("Percentage of ADA tokens by Price Range")
  currentCost = distribution["Cost"].sum()
  currentQuantity = distribution["Quantity"].sum()
  weightedPrice = currentCost / currentQuantity
  plt.title("Cost Basis: \$${0:,.2f}, Weighted Price: \$${1:,.2f}".format(currentCost, weightedPrice), y=1.0)
  plt.show()

def plotMultiDistribution(distributions: List[Tuple[str, Distribution]]) -> None:
  fig, axs = plt.subplots(nrows=2, ncols=2)
  fig.suptitle("Price Distribution across Assets")
  ax = [ axs[0, 0], axs[0, 1], axs[1, 0], axs[1, 1] ]
  i = 0
  for d in distributions:
    dist = d[1].groupby(["Percentile"])["Quantity"].sum().reset_index()  
    palette_color = sns.color_palette('bright')
    ax[i].pie(dist["Quantity"], labels=dist["Percentile"], colors=palette_color, autopct='%.0f%%')
    currentCost = d[1]["Cost"].sum()
    currentQuantity = d[1]["Quantity"].sum()
    weightedPrice = currentCost / currentQuantity
    ax[i].set_title("{0}\nCost Basis: \$${1:,.2f}, Weighted Price: \$${2:,.2f}".format(d[0], currentCost, weightedPrice), y=1.0)
    i += 1

  plt.show()