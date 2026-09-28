# LunaRide: Authorization Rate Triage & Recovery Plan

**Prepared by:** Yuno Technical Account Management · **For:** Sofia Chen (Head of Payments), Marco Delgado (CTO)
**Scope:** 30 days of data, 11 markets, 3 acquirers · **Status:** Day 30. Authorization rate at 57%, down from 79%.

---

## TL;DR

- **Main cause (~13 of 22 pts):** the Day 18 change from "exempt rides under $30" to **"challenge all transactions" with 3DS**. Failed or abandoned authentications (code 100) went from **4.2% to 29.0% of card declines**, about **183K extra failed payments in 10 days**. The drop hit **only cards**. Wallets, PIX and OXXO held steady or rose.
- **Amplifier (~4 pts): Yuno's own retry configuration.** Retrying "do not honor" (05) and timeouts (91) up to 2x per acquirer, then cascading, sends repeat attempts to issuers that are already declining. That trips velocity limits (code 65 = 11.2% of declines) and inflates the number of attempts.
- **Worsening factor (~2 pts, LATAM):** 6 Adyen LATAM MIDs have expired certificates. Found Day 28 and **still not fixed**.
- **Unexplained (~3 pts):** most likely 3DS *technical* failures. Suspects are app v4.8 (Day 8) combined with Adyen's 3DS2 protocol update (Day 12). Diagnostics are in the P1 actions.
- **Tokenization (Marco's theory)** is a **real, long-running leak, but it did not cause this drop.** Token-related hard declines (14 + 54) are only 4.1% of declines, and the 40% refresh rate existed before the drop. It belongs on the roadmap (P2) and does not need emergency handling.
- **Recovery path:** P0 fixes → **~74% within 7 days (+17 pts, ≈$216K/week)**. P1 → **~77%**. P2 → **~79%, back to baseline**. The proactive items could take it **past the old baseline (~81–83%)**.

> **Revenue convention used throughout:** LunaRide's own estimate of $280K/week lost for 22 pts gives **≈$12.7K/week (≈$55K/month) per authorization-rate point.** This is conservative. The gross figure is higher (see Data Notes).

---

## 1. Root Cause Analysis

### 1.1 What changed, and when

| Day | Event | Visible auth impact? |
|---|---|---|
| 8 | LunaRide app v4.8 (new checkout UX) | None. Days 1–20 average held at 79% |
| 12 | Adyen 3DS2 protocol update (industry-wide) | None on its own |
| 14 | Yuno raises retries on code 91 from 1 to 2 | None on its own, but it amplifies later failures |
| **18** | **3DS rule: "exempt <$30" → "challenge all"** | **Drop starts ~3 days later** |
| 21 | Auth rate 79% → 68% | |
| 28 | Adyen: 6 LATAM MIDs need a credential refresh (not fixed) | Adds LATAM failures late in the period |
| 30 | 57% | |

The changes on Days 8, 12 and 14 each ran for 4–10 days while the rate stayed at its ~79% baseline. The decline begins only after Day 18. Timing alone points to the 3DS rule. The five data cuts below confirm it independently.

### 1.2 Evidence triangulated across five dimensions

**① By payment method: only products that go through 3DS broke.**

| Method | Before | After | Δ |
|---|---|---|---|
| Visa/Mastercard | 78% | 56% | **−22** |
| Local debit cards | 76% | 58% | **−18** |
| PIX / GrabPay / GCash / OXXO (weighted, 413K txns) | 87.0% | 88.0% | **+1** |

APMs pass through the same Yuno orchestration layer and the same app, yet they *improved*. That rules out a platform-wide Yuno outage, a general app checkout bug, or a demand shock. What failed is specific to the card authentication path.

**② By acquirer: all three dropped by a similar amount, so the problem sits upstream of the acquirers.**

| Acquirer | Before | After | Δ |
|---|---|---|---|
| Adyen (primary) | 81% | 61% | −20 |
| dLocal (LATAM fallback) | 74% | 49% | −25 |
| Stripe (SEA + backup) | 76% | 53% | −23 |

If Yuno had been sending traffic to a bad acquirer, or Adyen's protocol update were the cause, one acquirer would stand out. All three fell 20–25 pts, which means the cause sits *before* acquirer selection. 3DS rules are applied at the Yuno/merchant layer, before routing. dLocal's larger drop fits its role as a fallback. It only receives transactions Adyen has already declined, so it gets the hardest traffic, and it cannot use Adyen-held card-on-file tokens (see 1.4).

**③ By country: the damage tracks each market's card dependence.**

- 9 card-heavy markets fell **19–23 pts** (e.g., Peru 76→54, Argentina 74→51, Thailand 82→61, Chile 80→58).
- **Mexico fell only 8 pts** (81→73). OXXO makes up 31% of its volume and held at 88%. Mexico's *card-only* rate works out to **78%→66% (−12)**.
- **Brazil fell only 1 pt** (83→82). PIX is 60% of its volume at 91%. Brazil cards work out to **73%→69% (−4)**. *Open question:* this is much milder than other markets. We should confirm whether the new 3DS rule actually reached Brazilian card traffic. If it did, Brazil's mature in-app 3DS2 issuers handle challenges far better than the rest, which also tells us something useful.

**④ By issuer BIN: nine domestic issuers in nine countries collapsed at the same time.**

| | Before | After | Δ |
|---|---|---|---|
| Top 9 declining BINs (337K txns, 22% of card volume) | 76.3% | 42.5% | **−34** |

These nine BINs are **22% of card volume but 34% of all lost card approvals** (114K of 336K). Bancolombia, BBVA Peru, BancoEstado, Galicia, BDO, Mandiri, Kasikorn, Techcombank and Maybank do not have outages together. What they share is heavy domestic debit use and challenge flows that depend on SMS OTP or a switch to the bank app. For a rider booking a ~$5 ride at the curb, that friction leads to abandonment. None of the nine is in Mexico or Brazil, the two markets that held up.

**⑤ By decline code: the 3DS spike accounts for most of the new declines.**

- Total card declines, Days 21–30: **683,352** (this reconciles with 56% on 1,421K Visa/MC plus 58% on 131K local debit, ≈680K).
- Estimated declines at the old rates on the same volume: **~344K**. **Incremental declines: ~339K.**
- Code 100: ~14.5K before (4.2%) vs **197,834 after (29.0%)**, **+183K**. That is **~54% of all incremental declines from this one code**, before counting its knock-on effects (riders re-attempting, which feeds 05, 65 and 91).

### 1.3 Attribution of the 22-point drop (estimated)

| Driver | Est. pts | ≈ $/week | Confidence | Owner |
|---|---|---|---|---|
| "Challenge all" 3DS rule (code 100 plus follow-on re-attempts) | **~13** | ~$165K | High: timing, method, acquirer, BIN and code data all agree | LunaRide config |
| Retry and cascade amplification (05/91 retried 2x per acquirer → velocity 65, issuer throttling) | **~4** | ~$51K | Medium: before-period code mix not provided | **Yuno** (Day 14 change + standing config) |
| Adyen expired certificates, 6 LATAM MIDs | **~2** | ~$25K | Medium: late-period only, still unresolved | Adyen / LunaRide / Yuno |
| Unexplained: likely 3DS technical failures (app v4.8 × Adyen protocol) | **~3** | ~$38K | Low: needs the diagnostics in P1-1 | TBD |
| **Total** | **22** | **~$280K** | | |

*Method:* code 100 alone explains ~54% of incremental declines, and challenge abandonment also generates re-attempts that show up under other codes, so 3DS gets ~13 of 22 pts (~60%). The remaining points are split by timing and mechanism. Every row is validated within 72 hours of its P0 fix going live (see Action Plan).

### 1.4 Verdict on the three competing theories

| Theory | Verdict | Why |
|---|---|---|
| **Sofia: the new 3DS rules** | **Primary cause** | Strongest on all five data cuts. Her *motive* is valid: Colombia chargebacks rose 0.8%→1.4%, close to Mastercard's 1.5% Excessive Chargeback threshold. The *tool* was too blunt. She challenged 100% of traffic, including returning riders with saved cards and ~$5 tickets, to fix a problem in one market. |
| **Marco: tokenization / stale cards** | **Real, long-running, but did not cause this drop** | Expired (54) plus invalid card (14) = **27.7K, 4.1% of declines**. The 40% token-refresh rate predates the incident, so it cannot produce a 10-day cliff, and it would appear as spikes in 54/14, not in 100. *But* he is right that it matters strategically. Acquirer-held tokens also make cross-acquirer failover weaker for the **68% of volume that is card-on-file** (a token held by Adyen cannot be charged through dLocal). → P2, with the cost-benefit below. |
| **Yuno routing logic** | **Not the root cause, but a real amplifier. Yuno owns this.** | Uniform drops across acquirers and healthy APMs rule out bad routing. However, our retry rules resend 05 (generic decline) to the same acquirer and retry 91 twice. When issuers are already declining because of 3DS, that repetition trips velocity limits (code 65, **76.5K, 11.2%**) and wastes attempts. Retry-sensitive codes 05 + 91 + 65 = **45% of declines**. |

### 1.5 Data notes (caveats worth flagging to the merchant)

1. **Attempts ≠ payments.** Days 21–30 show **1,965K** attempts. LunaRide's run-rate of 2.8M payments/month is ~933K per 10 days, so that is **~2.1 attempts per ride payment.** The reported authorization rate counts attempts, and retries and cascades inflate the denominator. We will report both **attempt-level** and **payment-level (unique order) conversion** from now on.
2. **57% vs 64%.** The volume-weighted average for Days 21–30 is **64.1%**. The headline 57% is the **Day 30 spot rate**. The two are consistent: the rate slid from 68% (Day 21) to 57% (Day 30), and the MID issue added to the slide late in the period. The trend is still getting worse, which is why the P0 items matter.
3. **$280K/week is a net figure.** At a ~$5 average ticket ($14M ÷ 2.8M), 22 pts of ~646K weekly payments is ~142K failed rides, or ~$711K gross. LunaRide's $280K implies many riders recover by retrying or switching methods. We use $280K so we don't overstate.
4. Only code 100 has a before-period baseline, so attribution for the other codes is estimated. Local debit (131K) does not appear in the acquirer table.

---

## 2. Technical Action Plan

**Targets:** P0 → ~74% (+17 pts) within 7 days · P1 → ~77% (+3) within 2 weeks · P2 → ~79% (+1.5) within 6 weeks.
**Guardrail for every change:** canary at 20% of traffic for 24h, then 100%, with auth rate, code 100 share, and Colombia fraud/chargeback signals watched throughout.

### P0: Do immediately (0–72 hours)

| # | Action | Owner | Expected impact | Effort / timeline |
|---|---|---|---|---|
| **P0-1** | **Replace "challenge all" with risk-based 3DS.** (a) Restore the exemption / "no challenge requested" preference for rides **<$30**, which covers almost all traffic at a ~$5 average ticket. (b) **Keep challenges only where risk sits:** Colombia first-use cards, new device or card combinations, cards with prior chargebacks, amounts >$30, and high fraud-score transactions. (c) For **technical** authentication failures (3DS status U, timeout, challenge UI error), fall back to a single frictionless or non-3DS attempt where no local mandate applies. Never do this on an explicit authentication failure (status N/R). | LunaRide approves (Sofia). **Yuno configures** in the dashboard | **+11 pts ≈ $140K/week** (keeps ~2 of the ~13 pts as the deliberate cost of Colombia protection) | Config only. Canary Day 1, full rollout Day 2, measurable by Day 3 |
| **P0-2** | **Fix the retry and cascade rules.** Revert the Day 14 change (91: 2 retries → 1, with backoff, then cascade). **Stop same-acquirer retries on 05**. Cascade once to the alternate acquirer instead. **Never retry** 14 / N7 / 54 (hard) or 65 (velocity) or 100 (authentication). No immediate retry on 51/61 (see Proactive #1). Honor Mastercard Merchant Advice Codes (e.g., "do not retry"). Stay within Visa's excessive-reattempt limits to avoid network fees. | **Yuno** (our config; we own it) | **+4 pts ≈ $51K/week.** Also lowers attempts per ride (~2.1x) and per-attempt processing fees | Hours to configure. Live within 24h |
| **P0-3** | **Adyen certificate refresh for the 6 LATAM MIDs.** Until it's done, **Yuno marks these MIDs unhealthy and sends their traffic straight to dLocal** (circuit breaker), so configuration errors stop being retried as if they were issuer declines. | **Adyen** issues credentials → **LunaRide** uploads them to the Yuno dashboard → **Yuno** validates and re-enables | **+2 pts ≈ $25K/week** (LATAM) | Circuit breaker today. Credential refresh 24–72h, depending on Adyen |
| **P0-4** | **Daily war-room metric pack** (shared with Sofia and Marco): auth rate by country × method × acquirer, code 100 share, attempts per payment, Colombia fraud and chargeback alerts. | Yuno | Confirms each estimate above. Rolls back quickly if Colombia fraud rises | 1 day |

**P0 total: +17 pts → ~74%, ≈ $216K/week recovered (~$0.9M/month).**

### P1: This week

| # | Action | Owner | Expected impact | Effort |
|---|---|---|---|---|
| **P1-1** | **3DS failure diagnostics to explain the unexplained ~3 pts.** Break code 100 down by 3DS transaction status (C = challenge abandoned vs N = failed vs U = technical), **app version (v4.8 vs older)**, iOS/Android/web, **3DS protocol version since Adyen's Day 12 update**, challenge type (SMS OTP vs bank app) and issuer. Run a QA test of challenge rendering in v4.8 against the new protocol. | Yuno (data) + **LunaRide Eng** (SDK/app) + Adyen (protocol) | Recover the remaining **~3 pts ≈ $38K/week** if a technical fault is confirmed | 2–3 days to analyze. Hotfix timing depends on the root cause |
| **P1-2** | **Richer 3DS2 data for the 9 problem BINs.** Send the full optional data set (device ID, phone, email, billing address, account age, ride history) so issuers approve more transactions without a challenge. Open issuer-relations tickets through Adyen/dLocal with Bancolombia, BBVA Peru, BDO and others. | Yuno + LunaRide (data fields) + acquirers | Part of the P1-1 recovery, focused on the 337K-txn BIN group that is now at 42.5% | 3–5 days |
| **P1-3** | **Colombia fraud controls without friction** (so Sofia keeps her protection): device fingerprinting and a fraud score in Yuno, chargeback alerts (Ethoca / Verifi RDR) to refund before a dispute is filed, and **ride-specific evidence** (GPS trip trace, driver ID, pickup/drop-off) in dispute responses. | LunaRide Payments + Yuno | Keeps Colombia under the 1.5% chargeback threshold without a blanket challenge. Protects the +11 pts from P0-1 | 1 week |
| **P1-4** | **Change management:** any 3DS, routing or retry change requires sign-off from both Payments and Engineering, a canary rollout, and auto-rollback if auth rate drops >3 pts. | LunaRide (Sofia + Marco) + Yuno | Prevents a repeat. Ends the disagreement over who approves what | 1 meeting |

**P1 total: +3 pts → ~77%, ≈ $38K/week.**

### P2: Next sprint (2–6 weeks)

| # | Action | Owner | Expected impact | Effort |
|---|---|---|---|---|
| **P2-1** | **Tokenization program:** (a) **Network tokens** (Visa VTS / Mastercard MDES), which update automatically when a card is reissued. (b) **Account updater** (Visa VAU / Mastercard ABU) for any remaining PANs. (c) Move card-on-file credentials from **acquirer-held to orchestrator-level (Yuno vault) tokens**, so any acquirer can charge the 68% card-on-file volume and cascades actually work. | **LunaRide Eng** (backend migration) + Yuno (vault/network tokens) + acquirers (token export) | Token refresh 40% → 85%+. Recovers most of the 27.7K declines on 14/54 per 10 days, **~+1.5 pts ≈ $19K/week (~$1M/year)**, plus better fallback performance on dLocal/Stripe | 4–6 weeks, ~2 engineers |

### Cost-benefit summary (for Marco's Friday roadmap meeting)

| Initiative | Eng effort | Pts | $/week | Rank by ROI |
|---|---|---|---|---|
| P0-1 Risk-based 3DS | ~0 (config) | +11 | ~$140K | 1 |
| P0-2 Retry rules | ~0 (Yuno config) | +4 | ~$51K | 2 |
| P0-3 MID certificates + circuit breaker | ~0 | +2 | ~$25K | 3 |
| P1-1/1-2 3DS diagnostics + data enrichment | Days | +3 | ~$38K | 4 |
| **P2-1 Tokenization** | **4–6 weeks** | **+1.5** | **~$19K** (~$1M/yr) | 5, but **strategic**: needed for resilient multi-acquirer failover |

**How to frame it with Marco:** tokenization is the right *roadmap* bet. At ~$1M/year for ~10 engineer-weeks it pays back quickly, and it is required for true multi-acquirer resilience. It is not what fixes this incident. The configuration fixes recover about 10× more revenue at close to zero engineering cost, so they go first.

---

## 3. Merchant-Facing Communication (email to Sofia)

> **Subject:** Auth rate drop: root cause found, recovery to ~74% within 7 days (plan inside)
>
> Hi Sofia,
>
> We've finished the investigation. Here's what you need for your CFO and for Friday.
>
> **Bottom line**
> - We found **three causes** and can fix **~17 of the 22 lost points (~$216K/week) within 7 days**, with close to zero engineering work.
> - We expect to be **back to ~79% within 6 weeks**.
>
> **What happened**
> 1. **The "challenge all" security check is the main cause (~13 pts).** Since Day 18, every card payment asks the rider for a bank code or app approval, including returning riders paying ~$5 for a ride. Many don't finish that step. Failed security checks went from **4% to 29% of all declines**. Wallets, PIX and OXXO don't use this check, and they didn't drop at all.
> 2. **Our retry settings made it worse (~4 pts).** That's on Yuno. We were retrying declined cards too aggressively, which led some banks to block further attempts. We're fixing this today.
> 3. **Six Adyen merchant accounts in LATAM have expired certificates (~2 pts).** Adyen found this on Day 28. It's still open.
> 4. **~3 pts are still unexplained.** We suspect the new app version and Adyen's recent security-protocol update aren't working well together. We're checking this with your engineers this week.
>
> **Your fraud concern is valid, and we'll keep protecting Colombia.** Colombia chargebacks at 1.4% are close to Mastercard's 1.5% penalty threshold. We'll keep security checks where the risk is (new cards in Colombia, new devices, rides over $30, cards with past disputes) and turn them off for everyone else. Excess Colombia chargebacks cost roughly **~$33K/month**. The blanket rule is costing **~$165K/week**.
>
> **What we need from you**
> - ✅ **Today:** approve the targeted security-check rule. We'll roll it out to 20% of traffic first and watch fraud signals for 24h before going to 100%.
> - ✅ **Today:** ask your team to upload the new Adyen credentials to the Yuno dashboard once Adyen sends them. We're routing those accounts to dLocal in the meantime.
> - ✅ **This week:** give us 1 engineer for 2–3 days to check how the app's security-check screens work since the v4.8 release.
>
> **For your CFO:** the losses have a cause, and the fix is configuration, not a rebuild. Expected recovery is ~$216K/week within 7 days and ~$280K/week within 6 weeks. We'll send a daily dashboard until we're back at baseline.
>
> **For your conversation with Marco:** you both identified real issues. The security-check rule is the urgent fix. Marco's card-token upgrade is a sound ~$1M/year roadmap investment, just not the cause of this drop. We've included a cost-benefit table he can take to Friday's meeting, and we'd suggest a joint 30-minute call tomorrow to agree the plan and a shared sign-off process for future payment-rule changes.
>
> Full analysis attached. I'm available anytime today.
>
> Best,
> [Name], Technical Account Manager, Yuno

---

## 4. Proactive Optimization Recommendations

### 4.1 Smart retries for "insufficient funds" (≈ +1.3–2.0 pts, ≈ $17–25K/week)
- **Insufficient funds (51) and withdrawal limit (61) = 131K declines per 10 days (19.2%)**, the largest group of soft declines after 3DS. Retrying these within seconds almost never works and adds to velocity blocks.
- **Opportunity:** for post-trip charges, schedule retries **around local paydays** (e.g., the *quincena* on the 15th and the last day of the month in Mexico and Colombia) and at the times of day each issuer tends to approve. Combine this with an in-app "settle your ride" prompt that offers the rider's wallet, PIX or OXXO.
- **Impact:** recovering 20–30% of these declines = **26–39K approvals per 10 days ≈ +1.3–2.0 pts**. It also reduces bad debt from completed rides that were never paid for.
- **Owner:** Yuno (retry scheduler, MAC-aware) + LunaRide (unpaid-ride flow).

### 4.2 Expand local payment methods in the 9 card-dependent markets (≈ +0.5–1 pt, lower costs and chargebacks)
- **The crisis showed how much payment mix protects revenue:** Brazil (60% PIX) lost 1 pt and Mexico (31% OXXO) lost 8, while card-heavy markets lost 19–23. APMs held at **87–88%** throughout.
- **Candidates:** Colombia **Nequi / PSE**, Peru **Yape / Plin**, Argentina **Mercado Pago**, Chile **MACH**, Indonesia **GoPay / OVO / DANA / QRIS**, Thailand **PromptPay / TrueMoney**, Vietnam **MoMo / ZaloPay**, Malaysia **Touch 'n Go / DuitNow QR**, Philippines **Maya** (GCash is already live). For rides, prefer **linked or tokenized wallet** flows, which give one-tap payment after the first link, over redirect-per-payment flows.
- **Impact:** moving 15% of card volume in the 9 markets (~182K of ~1,216K txns per 10 days) to wallets at ~85% vs the ~78% card baseline adds **+0.5–1 pt**. Push payments also avoid card chargebacks, which helps Colombia directly. Wallet and A2A fees are often below card fees (to be confirmed per contract). *Quick check:* SPEI is enabled in Mexico but has no volume in the data, so it is worth finding out why.
- **Owner:** Yuno (integrations, all through the existing SDK) + LunaRide (checkout placement).

### 4.3 Performance-based routing and fewer wasted attempts (resilience plus lower processing cost)
- **Today:** a static "Adyen first everywhere" setup, ~2.1 attempts per ride, and card-on-file tokens that only work at the acquirer that issued them.
- **Opportunity:** (a) switch to **Yuno smart routing driven by real-time approval rates per BIN × country**, starting with an A/B test on the 9 problem BINs, comparing local acquiring (e.g., dLocal's in-country processing) against Adyen. (b) When approval rates are equal, route on **cost** (MDR, cross-border and FX fees). (c) After P0-2 and P2-1, target **≤1.4 attempts per payment.**
- **Impact:** +2–3 pts on the 337K-txn BIN group (~+0.3–0.5 pts overall). Cutting ~0.7 attempts per ride removes **~2M attempts per month**. *Illustrative: every $0.01 of per-attempt fee is ~$20K/month saved* (depends on LunaRide's acquirer contracts). It also means that if one acquirer degrades (like the MID incident), traffic is rerouted automatically instead of failing.
- **Owner:** Yuno.

---

*Appendix: every derived figure in this document can be reproduced from the scenario tables with `analysis/verify_numbers.py`.*
