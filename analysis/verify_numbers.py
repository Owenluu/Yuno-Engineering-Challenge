"""Recompute every derived number used in the LunaRide write-up from the raw scenario tables."""
countries = {  # before, after, volume (K txns, days 21-30)
 "Mexico":(81,73,287),"Colombia":(78,59,193),"Brazil":(83,82,341),"Peru":(76,54,108),
 "Chile":(80,58,142),"Argentina":(74,51,97),"Philippines":(77,56,201),"Indonesia":(79,60,188),
 "Thailand":(82,61,156),"Vietnam":(78,57,134),"Malaysia":(80,59,118)}
methods = {"Visa/MC":(78,56,1421),"PIX":(90,91,203),"GrabPay":(83,84,67),"GCash":(81,82,54),
 "OXXO":(87,88,89),"Local debit":(76,58,131)}
acq = {"Adyen":(81,61,847),"dLocal":(74,49,341),"Stripe":(76,53,233)}
bins = {"Bancolombia":(76,38,47),"BBVA Peru":(74,41,31),"BancoEstado":(78,44,38),"Galicia":(71,36,29),
 "BDO":(75,43,52),"Mandiri":(77,47,41),"Kasikorn":(80,45,37),"Techcombank":(76,42,34),"Maybank":(79,46,28)}
codes = {"51":89234,"05":127651,"14":21456,"91":103289,"65":76542,"N7":18923,"100":197834,"61":42189,"54":6234}

def wavg(d, i): return sum(v[i]*v[2] for v in d.values())/sum(v[2] for v in d.values())
tot = sum(v[2] for v in countries.values())
print(f"Total volume d21-30: {tot}K | methods sum {sum(v[2] for v in methods.values())}K")
print(f"Country-weighted auth: before {wavg(countries,0):.1f}% after {wavg(countries,1):.1f}%")
print(f"Method-weighted auth:  before {wavg(methods,0):.1f}% after {wavg(methods,1):.1f}%")
print(f"Acquirer-weighted auth: before {wavg(acq,0):.1f}% after {wavg(acq,1):.1f}%  vol {sum(v[2] for v in acq.values())}K")
print(f"Attempts per 10d vs 2.8M/mo stated: {tot/(2800/3):.2f}x")
# card-only splits for cushioned markets
br_c = 341-203; mx_c = 287-89
print(f"Brazil cards: before {(341*.83-203*.90)/br_c*100:.1f}% after {(341*.82-203*.91)/br_c*100:.1f}% ({br_c}K)")
print(f"Mexico cards: before {(287*.81-89*.87)/mx_c*100:.1f}% after {(287*.73-89*.88)/mx_c*100:.1f}% ({mx_c}K)")
apm = {k:v for k,v in methods.items() if k in("PIX","GrabPay","GCash","OXXO")}
print(f"APMs: before {wavg(apm,0):.1f}% after {wavg(apm,1):.1f}% vol {sum(v[2] for v in apm.values())}K")
# BINs
bv = sum(v[2] for v in bins.values())
print(f"Top-9 BINs: vol {bv}K before {wavg(bins,0):.1f}% after {wavg(bins,1):.1f}%")
bin_lost = sum(v[2]*(v[0]-v[1])/100 for v in bins.values())
card_lost = 1421*.22 + 131*.18
print(f"Lost card approvals: {card_lost:.0f}K; top-9 BINs lost {bin_lost:.0f}K = {bin_lost/card_lost*100:.0f}%; BIN share of card vol {bv/1552*100:.0f}%")
# declines
dec = sum(codes.values())
print(f"Total card declines d21-30: {dec:,}; implied from rates: {(1421*.44+131*.42)*1000:,.0f}")
dec_before = (1421*.22+131*.24)*1000
c100_before = .042*dec_before
print(f"Est. declines d1-20 (same vol): {dec_before:,.0f}; code100 before ~{c100_before:,.0f}")
inc = dec-dec_before; inc100 = codes['100']-c100_before
print(f"Incremental declines {inc:,.0f}; incremental code100 {inc100:,.0f} = {inc100/inc*100:.0f}%")
hard = codes['14']+codes['N7']+codes['54']
print(f"Hard declines {hard:,} = {hard/dec*100:.1f}%; token-related (14+54) {codes['14']+codes['54']:,} = {(codes['14']+codes['54'])/dec*100:.1f}%")
print(f"51+61 insufficient/limit: {codes['51']+codes['61']:,} = {(codes['51']+codes['61'])/dec*100:.1f}%")
print(f"Retry-sensitive 05+91+65: {codes['05']+codes['91']+codes['65']:,} = {(codes['05']+codes['91']+codes['65'])/dec*100:.1f}%")
# money
wk = 280_000; print(f"$ per auth point per week: {wk/22:,.0f}; per month {wk/22*52/12:,.0f}")
print(f"Avg ticket: ${14e6/2.8e6:.2f}; weekly GMV ${14e6*12/52:,.0f}")
col_gmv = 14e6*193/tot; col_tx = col_gmv/5
print(f"Colombia GMV/mo ~${col_gmv:,.0f}; txns {col_tx:,.0f}; excess CB (0.6%) {col_tx*.006:,.0f}/mo -> ${col_tx*.006*20:,.0f}/mo at $20/dispute")
