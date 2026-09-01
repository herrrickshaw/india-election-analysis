import pandas as pd

national_trend = [
    (2014, 834_000_000, 66.40, 553_801_801, 543),
    (2019, 911_000_000, 67.11, 614_000_000, 542),
    (2024, 968_800_000, 66.80, 646_400_000, 543),
]

ndf = pd.DataFrame(national_trend, columns=["Year","Total_Electors","Turnout_Pct","Votes_Cast","LS_Seats"])
ndf["Avg_Electors_per_Seat"] = ndf["Total_Electors"] / ndf["LS_Seats"]
ndf.to_csv("national_trend.csv", index=False)
print(ndf.to_string())
