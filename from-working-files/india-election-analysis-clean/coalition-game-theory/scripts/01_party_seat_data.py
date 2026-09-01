import pandas as pd
from itertools import combinations

# Current Lok Sabha party strength, post TMC-split (as of late June 2026)
# Base: Wikipedia "List of members of the 18th Lok Sabha" as of 28 March 2026,
# adjusted for: 20 TMC MPs -> merged into NCPI (joined NDA), 6 SS(UBT) MPs -> migrated to SHS (NDA)
# Net effect per NDA Wikipedia summary: NDA 292 -> 318; AITC 28 -> 8; SS(UBT) 9 -> 3; SHS 7 -> 13
# NCPI appears as new NDA-aligned party with 20 seats (pre-existing registered party, not newly formed)

parties = [
    # name, seats, bloc  (bloc: NDA / INDIA / UNALIGNED)
    ("BJP", 240, "NDA"),
    ("TDP", 16, "NDA"),
    ("JD(U)", 12, "NDA"),
    ("NCPI", 20, "NDA"),       # ex-TMC rebels, merged into pre-existing NCPI, joined NDA
    ("SHS", 13, "NDA"),        # Shiv Sena (Shinde) - 7 original + 6 ex-UBT migrants
    ("LJP(RV)", 5, "NDA"),
    ("JD(S)", 2, "NDA"),
    ("JSP", 2, "NDA"),
    ("RLD", 2, "NDA"),
    ("AD(S)", 1, "NDA"),
    ("AGP", 1, "NDA"),
    ("AJSU", 1, "NDA"),
    ("HAM(S)", 1, "NDA"),
    ("NCP", 1, "NDA"),
    ("SKM", 1, "NDA"),
    ("INC", 98, "INDIA"),
    ("SP", 37, "INDIA"),
    ("AITC", 8, "INDIA"),      # TMC remainder after 20-MP split
    ("DMK", 22, "INDIA"),
    ("SS(UBT)", 3, "INDIA"),   # remainder after 6 migrated out
    ("NCP-SP", 8, "INDIA"),
    ("CPI(M)", 4, "INDIA"),
    ("RJD", 4, "INDIA"),
    ("IUML", 3, "INDIA"),
    ("JMM", 3, "INDIA"),
    ("CPI", 2, "INDIA"),
    ("CPI(ML)L", 2, "INDIA"),
    ("JKNC", 2, "INDIA"),
    ("VCK", 2, "INDIA"),
    ("BAP", 1, "INDIA"),
    ("KEC", 1, "INDIA"),
    ("MDMK", 1, "INDIA"),
    ("RLP", 1, "INDIA"),
    ("RSP", 1, "INDIA"),
    ("IND(INDIA-aligned)", 3, "INDIA"),
    ("YSRCP", 4, "UNALIGNED"),
    ("AAP", 3, "UNALIGNED"),
    ("AD(WPD)", 2, "UNALIGNED"),
    ("AIMIM", 1, "UNALIGNED"),
    ("ASP(KR)", 1, "UNALIGNED"),
    ("SAD", 1, "UNALIGNED"),
    ("UPPL", 1, "UNALIGNED"),
    ("ZPM", 1, "UNALIGNED"),
    ("JKAIP", 1, "UNALIGNED"),
    ("IND(other)", 1, "UNALIGNED"),
]

df = pd.DataFrame(parties, columns=["Party", "Seats", "Bloc"])
df["Vacant_adj"] = 0
total = df["Seats"].sum()
vacant = 543 - total
print(f"Total accounted: {total}, Vacant: {vacant}")  # 3 vacant seats (Basirhat, Shillong, Nagaon)

bloc_totals = df.groupby("Bloc")["Seats"].sum()
print(bloc_totals)
print("Majority threshold (of 543):", 543//2 + 1)
print("Majority threshold (of 540, excl. 3 vacant):", 540//2 + 1)

df.to_csv("party_seats.csv", index=False)
