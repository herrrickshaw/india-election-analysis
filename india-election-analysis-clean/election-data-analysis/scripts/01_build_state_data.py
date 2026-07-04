import pandas as pd

# State-wise data: LS seats, 2011 Census population, Assembly (Vidhan Sabha) seats
# Sources: Wikipedia "List of constituencies of the Lok Sabha" (2011 Census/seats),
# gkchronicle.com (Assembly seats), ECI 2024 statistical reports (electors - aggregated from constituency-level)

data = [
    # State, LS_Seats, Census2011_Pop, Assembly_Seats
    ("Andhra Pradesh", 25, 49577103, 175),
    ("Arunachal Pradesh", 2, 1383727, 60),
    ("Assam", 14, 31205576, 126),
    ("Bihar", 40, 104099452, 243),
    ("Chhattisgarh", 11, 25545198, 90),
    ("Goa", 2, 1458545, 40),
    ("Gujarat", 26, 60439692, 182),
    ("Haryana", 10, 25351462, 90),
    ("Himachal Pradesh", 4, 6864602, 68),
    ("Jharkhand", 14, 32988134, 81),
    ("Karnataka", 28, 61095297, 224),
    ("Kerala", 20, 33406061, 140),
    ("Madhya Pradesh", 29, 72626809, 230),
    ("Maharashtra", 48, 112374333, 288),
    ("Manipur", 2, 2570390, 60),
    ("Meghalaya", 2, 2966889, 60),
    ("Mizoram", 1, 1097206, 40),
    ("Nagaland", 1, 1978502, 60),
    ("Odisha", 21, 41974219, 147),
    ("Punjab", 13, 27743338, 117),
    ("Rajasthan", 25, 68548437, 200),
    ("Sikkim", 1, 610577, 32),
    ("Tamil Nadu", 39, 72147030, 234),
    ("Telangana", 17, 35003674, 119),
    ("Tripura", 2, 3673917, 60),
    ("Uttar Pradesh", 80, 199812341, 403),
    ("Uttarakhand", 5, 10086292, 70),
    ("West Bengal", 42, 91276115, 294),
    ("Andaman and Nicobar Islands", 1, 380581, None),
    ("Chandigarh", 1, 1055450, None),
    ("Dadra and Nagar Haveli and Daman and Diu", 2, 585764, None),
    ("Jammu and Kashmir", 5, 12267032, 90),
    ("Ladakh", 1, 274000, None),
    ("Lakshadweep", 1, 64473, None),
    ("Delhi", 7, 16787941, 70),
    ("Puducherry", 1, 1247953, 30),
]

df = pd.DataFrame(data, columns=["State", "LS_Seats_2024", "Census2011_Pop", "Assembly_Seats"])

# 2024 electors aggregated from constituency-level data pulled from Wikipedia (ECI 2024 statistical reports)
# These are sums of each state's constituency elector figures shown in the Lok Sabha constituency list
electors_2024 = {
    "Andhra Pradesh": 4_05_69_103,   # sum of 25 constituencies (approx aggregation, see notes)
    "Arunachal Pradesh": 8_98_442,
    "Assam": 2_55_07_074,
    "Bihar": 7_74_19_516,
    "Chandigarh": 6_60_552,
    "Chhattisgarh": 2_07_98_657,
    "Dadra and Nagar Haveli and Daman and Diu": 4_17_236,
    "Delhi": 1_57_15_238,
    "Goa": 11_79_644,
    "Gujarat": 4_90_56_558,
    "Haryana": 2_03_88_111,
    "Himachal Pradesh": 57_11_969,
    "Jammu and Kashmir": 88_02_348,
    "Jharkhand": 2_61_29_704,
    "Karnataka": 5_18_60_645,
    "Kerala": 2_77_18_447,
    "Ladakh": 1_90_576,
    "Lakshadweep": 57_953,
    "Madhya Pradesh": 5_67_69_780,
    "Maharashtra": 9_38_84_493,
    "Manipur": 20_51_357,
    "Meghalaya": 22_30_451,
    "Mizoram": 8_61_327,
    "Nagaland": 13_25_383,
    "Odisha": 3_38_19_452,
    "Puducherry": 10_24_024,
    "Punjab": 2_13_66_557,
    "Rajasthan": 5_36_61_578,
    "Sikkim": 4_66_643,
    "Tamil Nadu": 6_25_94_799,
    "Telangana": 3_13_47_026,
    "Tripura": 28_70_896,
    "Uttar Pradesh": 15_43_44_580,
    "Uttarakhand": 79_30_901,
    "West Bengal": 7_36_88_046,
    "Andaman and Nicobar Islands": 3_15_745,
}

df["Electors_2024"] = df["State"].map(electors_2024)
df.to_csv("state_data_raw.csv", index=False)
print(df.to_string())
print("\nTotal LS seats:", df["LS_Seats_2024"].sum())
print("Total 2024 electors:", df["Electors_2024"].sum())
print("Total 2011 Census pop:", df["Census2011_Pop"].sum())
