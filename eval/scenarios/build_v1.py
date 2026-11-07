"""Build the Pauseline benchmark v1 (synthetic, no real personal data).

Each scenario is one payment request: what the payer says, who they pay, how much, plus the
ground truth (scam or not, scam type) and how the payer would truthfully answer each
clarifying question. "Coached" scam victims deny everything, as scammers instruct them to.

Scam types follow public descriptions by the FBI IC3, the US FTC, and Indian advisories on
"digital arrest" scams (see EXPERIMENTS.md). Statements were drafted with AI assistance
(Claude) and reviewed by the team.

Run:  uv run python eval/scenarios/build_v1.py
Writes v1.jsonl and MANIFEST.json (sha256). Do not edit v1.jsonl by hand: change this file,
bump the version, and re-run, so the test split stays frozen and auditable.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent
US, IN = ("USD", 60.0), ("INR", 3000.0)


def S(label, scam_type, lang, statement, payee, known, amount, cur=US, risky=(), coached=False, rel="", recent=0, hour=None, median=None):
    return {
        "label": label,
        "scam_type": scam_type if label == "scam" else "none",
        "lang": lang,
        "statement": statement,
        "payee": {"name": payee, "known": known, "relationship": rel},
        "amount": amount,
        "currency": cur[0],
        "history_median": median if median is not None else cur[1],
        "recent_count_1h": recent,
        "hour_of_day": hour,
        "true_risky_answers": list(risky),
        "coached": coached,
    }


scam, ok = "scam", "benign"

SCENARIOS = [
    # ---------------------------------------------------------------- scams: bank / safe account
    S(scam, "bank_safe_account", "en", "The bank's fraud department called. They said my account is hacked and I must move my savings to a safe account they set up for me today.", "Account Protection Desk", False, 4800, risky=["someone_asked", "special_method", "verified_independently"]),
    S(scam, "bank_safe_account", "en", "Moving money to my new secure account at the bank, the manager said it's routine.", "J. Collins", False, 3000, risky=["someone_asked", "special_method", "on_call_now"], coached=True),
    S(scam, "bank_safe_account", "hinglish", "Bank se call aaya tha, unhone bola account block ho jayega, paise safe karne ke liye is account mein transfer karo abhi.", "RBI Safe Desk", False, 150000, cur=IN, risky=["on_call_now", "someone_asked", "special_method", "threatened"]),
    S(scam, "bank_safe_account", "hi", "बैंक वालों ने कहा मेरा खाता हैक हो गया है, पैसे सुरक्षित खाते में डालने हैं।", "Suraksha Account", False, 200000, cur=IN, risky=["someone_asked", "special_method", "threatened"]),
    S(scam, "bank_safe_account", "en", "Transferring to my other account for safety.", "M. Davis", False, 2500, risky=["someone_asked", "special_method", "on_call_now"], coached=True),
    S(scam, "bank_safe_account", "en", "The man from Visa security is still on the line, he needs me to send my balance so they can protect it.", "Card Security Team", False, 1900, risky=["on_call_now", "someone_asked", "special_method"]),
    # ---------------------------------------------------------------- scams: digital arrest / government impersonation
    S(scam, "digital_arrest_or_government", "en", "A customs officer said a parcel in my name had drugs. I'm on a video call with the CBI and must pay a verification deposit or I'll be arrested.", "Verification Deposit A/C", False, 300000, cur=IN, risky=["on_call_now", "threatened", "secrecy", "someone_asked"]),
    S(scam, "digital_arrest_or_government", "hinglish", "Mumbai police ka video call chal raha hai, bol rahe hain money laundering case hai, verification ke liye paise bhejne padenge, kisi ko mat batana.", "Cyber Cell Verification", False, 500000, cur=IN, risky=["on_call_now", "threatened", "secrecy", "someone_asked", "special_method"]),
    S(scam, "digital_arrest_or_government", "hi", "पुलिस अफसर ने कहा कि मेरे नाम पर केस है, गिरफ्तारी से बचने के लिए जुर्माना भरना होगा।", "Police Fine Account", False, 80000, cur=IN, risky=["threatened", "someone_asked", "on_call_now"]),
    S(scam, "digital_arrest_or_government", "en", "An IRS agent says I owe back taxes and a warrant will be issued today unless I pay.", "Treasury Collections Unit", False, 2200, risky=["threatened", "someone_asked", "verified_independently"]),
    S(scam, "digital_arrest_or_government", "en", "The Social Security office said my number was used in a crime and I need to pay to clear my name.", "SSA Case Resolution", False, 3500, risky=["threatened", "someone_asked", "on_call_now"]),
    S(scam, "digital_arrest_or_government", "en", "Paying a legal settlement, the officer explained everything.", "Federal Settlement Office", False, 4000, risky=["threatened", "on_call_now", "secrecy"], coached=True),
    S(scam, "digital_arrest_or_government", "hinglish", "TRAI se call aaya ki mera number band ho jayega aur FIR hogi, fine bharna hai turant.", "TRAI Compliance", False, 25000, cur=IN, risky=["threatened", "someone_asked"]),
    # ---------------------------------------------------------------- scams: family emergency
    S(scam, "family_emergency", "en", "My grandson called from a new number, he's in jail after an accident and the lawyer needs bail money today. He asked me not to tell his mom.", "Attorney Mark Reed", False, 3000, risky=["someone_asked", "secrecy", "verified_independently"]),
    S(scam, "family_emergency", "en", "Rahul lost his phone, he's messaging from this new number, stuck abroad and needs money for a ticket home.", "R. Sharma", False, 900, risky=["verified_independently", "secrecy"]),
    S(scam, "family_emergency", "hinglish", "Beta ka message aaya naye number se, hospital mein hai, jaldi paise bhejo bola.", "Hospital Payment", False, 40000, cur=IN, risky=["verified_independently", "someone_asked"]),
    S(scam, "family_emergency", "en", "Sending to my nephew's friend who is helping him out.", "Kevin Brooks", False, 1500, risky=["secrecy", "verified_independently", "someone_asked"], coached=True),
    S(scam, "family_emergency", "hi", "पोते का फ़ोन आया, नए नंबर से, वह मुसीबत में है और किसी को न बताने को कहा।", "Legal Help Account", False, 50000, cur=IN, risky=["secrecy", "verified_independently", "someone_asked"]),
    S(scam, "family_emergency", "en", "My granddaughter was arrested, the public defender called and said to pay the bond in gift cards.", "Bond Office", False, 2000, risky=["special_method", "secrecy", "someone_asked", "verified_independently"]),
    # ---------------------------------------------------------------- scams: tech support
    S(scam, "tech_support", "en", "Microsoft support said my computer has a virus, they connected with AnyDesk and need payment for the repair and protection plan.", "PC Shield Support", False, 400, risky=["on_call_now", "someone_asked", "verified_independently"]),
    S(scam, "tech_support", "en", "The refund agent is on my screen, they refunded me too much by mistake and I need to send back the difference.", "Refund Department", False, 1800, risky=["on_call_now", "someone_asked", "promised_money"]),
    S(scam, "tech_support", "hinglish", "Amazon customer care wale ne TeamViewer install karwaya, refund ke liye pehle charge dena hai.", "Refund Process Desk", False, 15000, cur=IN, risky=["on_call_now", "promised_money"]),
    S(scam, "tech_support", "en", "Paying for my computer security subscription.", "TechGuard Online", False, 499, risky=["on_call_now", "someone_asked"], coached=True),
    S(scam, "tech_support", "en", "My bank app was hacked, the technician said to buy Google Play cards to reset it.", "App Reset Service", False, 600, risky=["special_method", "on_call_now"]),
    # ---------------------------------------------------------------- scams: romance
    S(scam, "romance", "en", "My fiancé is on an oil rig overseas and needs money for customs to send his things. We met online but haven't met in person yet.", "James Whitfield", False, 2500, risky=["met_in_person", "someone_asked"]),
    S(scam, "romance", "en", "David needs money for his flight ticket to come visit me, we met on a dating app.", "David Moore", False, 1400, risky=["met_in_person", "someone_asked"]),
    S(scam, "romance", "en", "Helping a close friend with her medical bills.", "Daniel W.", False, 3000, risky=["met_in_person", "someone_asked", "secrecy"], coached=True),
    S(scam, "romance", "hinglish", "Online dost hai, army mein hai abroad, usko visa fee ke liye paise chahiye.", "Capt. Steve", False, 60000, cur=IN, risky=["met_in_person", "someone_asked"]),
    S(scam, "romance", "en", "Sending to Anna for her hospital bill, she's stuck in Turkey and I'm the only one she trusts.", "Anna Petrova", False, 2000, risky=["met_in_person", "someone_asked", "secrecy"]),
    S(scam, "romance", "hi", "ऑनलाइन मिले दोस्त को विदेश से आने के लिए पैसे चाहिए, हम कभी मिले नहीं।", "Michael John", False, 45000, cur=IN, risky=["met_in_person", "someone_asked"]),
    # ---------------------------------------------------------------- scams: prize / lottery
    S(scam, "prize_or_lottery", "en", "I won a car in a lucky draw and need to pay the processing fee to release it.", "Prize Release Office", False, 350, risky=["promised_money", "someone_asked"]),
    S(scam, "prize_or_lottery", "hinglish", "KBC lottery mein 25 lakh jeete hain, tax pehle bharna hai claim karne ke liye.", "KBC Prize Desk", False, 18000, cur=IN, risky=["promised_money", "someone_asked", "secrecy"]),
    S(scam, "prize_or_lottery", "hi", "मुझे इनाम मिला है, उसे पाने के लिए फीस भरनी है।", "Inaam Seva", False, 10000, cur=IN, risky=["promised_money"]),
    S(scam, "prize_or_lottery", "en", "The sweepstakes office says I'm a winner, there's just a release fee first.", "Sweepstakes Claims", False, 199, risky=["promised_money"]),
    S(scam, "prize_or_lottery", "en", "Paying an administration fee.", "Global Awards Center", False, 450, risky=["promised_money", "someone_asked"], coached=True),
    # ---------------------------------------------------------------- scams: investment / crypto
    S(scam, "investment_or_crypto", "en", "The investment group on WhatsApp guarantees 5% returns a day, I need to deposit more to unlock my withdrawal.", "Apex Wealth Club", False, 5000, risky=["promised_money", "met_in_person"]),
    S(scam, "investment_or_crypto", "en", "Buying bitcoin through the trading platform my friend from Telegram showed me.", "CoinRise Exchange", False, 3000, risky=["promised_money", "met_in_person", "special_method"]),
    S(scam, "investment_or_crypto", "hinglish", "Trading app mein profit dikh raha hai, withdraw fee bharni hai paisa nikalne ke liye.", "TradeMax Wallet", False, 70000, cur=IN, risky=["promised_money"]),
    S(scam, "investment_or_crypto", "en", "A chance to double my money, they said it's risk free.", "Prime Returns Ltd", False, 2000, risky=["promised_money", "someone_asked"]),
    S(scam, "investment_or_crypto", "en", "Topping up my investment account.", "Apex Digital Assets", False, 4500, risky=["promised_money", "met_in_person", "special_method"], coached=True),
    S(scam, "investment_or_crypto", "hi", "पैसे दोगुने करने वाली स्कीम में निवेश कर रही हूँ।", "Double Money Scheme", False, 100000, cur=IN, risky=["promised_money", "met_in_person"]),
    # ---------------------------------------------------------------- scams: fake refund / invoice
    S(scam, "fake_invoice_or_refund", "en", "Someone sent me 900 by mistake and asked me to return the extra to this account.", "T. Nguyen", False, 900, risky=["someone_asked", "verified_independently"]),
    S(scam, "fake_invoice_or_refund", "en", "The utility company called, my power will be cut off in an hour unless I pay this new account.", "City Power Services", False, 480, risky=["threatened", "someone_asked", "on_call_now"]),
    S(scam, "fake_invoice_or_refund", "hinglish", "Bijli wale ka message aaya, aaj raat connection kat jayega, is number pe bill bharo.", "Electricity Dept Payment", False, 8000, cur=IN, risky=["threatened", "verified_independently"]),
    S(scam, "fake_invoice_or_refund", "en", "Paying the overdue invoice from the supplier's new email, they changed their bank details.", "Office Supply Billing", False, 2400, risky=["verified_independently"]),
    # ---------------------------------------------------------------- scams: job / task
    S(scam, "job_or_task", "en", "Work from home job rating hotels, I need to deposit to unlock my earnings.", "TaskPro Rewards", False, 700, risky=["promised_money", "met_in_person"]),
    S(scam, "job_or_task", "hinglish", "Part time task job hai, YouTube videos like karne ke paise milte hain, aage badhne ke liye deposit chahiye.", "Task Earn Wallet", False, 12000, cur=IN, risky=["promised_money"]),
    S(scam, "job_or_task", "en", "Registration fee for the remote data entry job they offered me on Telegram.", "Remote Hiring Desk", False, 150, risky=["promised_money", "someone_asked"]),
    S(scam, "job_or_task", "en", "Paying for training materials for my new job.", "Remote Careers Hub", False, 300, risky=["promised_money", "someone_asked"], coached=True),
    S(scam, "tech_support", "hi", "कंप्यूटर ठीक करने वाले ने रिमोट ऐप डलवाया और पैसे मांगे।", "Computer Help Desk", False, 9000, cur=IN, risky=["on_call_now"]),
    # ---------------------------------------------------------------- scams that context rules miss: repeat payments to a scammer
    # the victim already saved as a payee, and small amounts below any threshold.
    S(scam, "investment_or_crypto", "en", "Another payment to the investment platform, they said I need to pay the tax before I can withdraw.", "Apex Wealth Club", True, 1500, risky=["promised_money", "met_in_person"], rel="investment"),
    S(scam, "romance", "en", "Second installment for David's customs clearance.", "David Moore", True, 1200, risky=["met_in_person", "someone_asked"], rel="friend"),
    S(scam, "digital_arrest_or_government", "hinglish", "Phir se verification charge, police wale bol rahe hain ye last time hai.", "Cyber Cell Verification", True, 100000, cur=IN, risky=["threatened", "on_call_now", "secrecy"]),
    S(scam, "romance", "en", "Monthly payment.", "Daniel W.", True, 800, risky=["met_in_person", "someone_asked", "secrecy"], coached=True, rel="friend"),
    S(scam, "tech_support", "en", "Buying two Google Play cards like the support man asked.", "Card Load Center", False, 200, risky=["special_method", "on_call_now"]),
    S(scam, "fake_invoice_or_refund", "en", "Small fee to release my parcel at customs, the delivery text had a link.", "Parcel Redelivery", False, 45, risky=["verified_independently"]),
    S(scam, "fake_invoice_or_refund", "hinglish", "Courier wale ka SMS aaya, redelivery charge bharna hai warna parcel wapas jayega.", "Courier Redelivery", False, 50, cur=IN, risky=["verified_independently"]),
    S(scam, "fake_invoice_or_refund", "en", "Paying the toll violation notice I got by text message.", "Toll Services Notice", False, 12, risky=["verified_independently", "threatened"]),
    # ---------------------------------------------------------------- benign: routine
    S(ok, "", "en", "Rahul's college books", "Rahul", True, 80, rel="grandson"),
    S(ok, "", "en", "Electricity bill for October", "City Electric", True, 95, rel="electricity bill"),
    S(ok, "", "en", "Doctor's consultation", "Dr. Mehta Clinic", True, 60, rel="doctor"),
    S(ok, "", "en", "Birthday gift for my granddaughter", "Priya", True, 50, rel="granddaughter"),
    S(ok, "", "en", "Monthly rent", "Mr. Kapoor", True, 900, rel="landlord", median=150),
    S(ok, "", "en", "Groceries money for the week", "Asha", True, 70, rel="daughter"),
    S(ok, "", "en", "Paying Susan back for lunch", "Susan", True, 25, rel="friend"),
    S(ok, "", "en", "Church donation", "St. Thomas Church", True, 40, rel="church"),
    S(ok, "", "en", "Gardener's monthly payment", "Green Thumb Gardening", True, 120, rel="gardener"),
    S(ok, "", "en", "Pharmacy bill", "Wellcare Pharmacy", True, 35, rel="pharmacy"),
    S(ok, "", "hinglish", "Bahu ko ghar ke kharche ke liye", "Neha", True, 5000, cur=IN, rel="daughter-in-law"),
    S(ok, "", "hinglish", "Doodh wale ka mahine ka hisaab", "Ramesh Dairy", True, 1800, cur=IN, rel="milkman"),
    S(ok, "", "hi", "बिजली का बिल", "MSEB", True, 2500, cur=IN, rel="electricity bill"),
    S(ok, "", "hi", "पोते की स्कूल फीस", "DPS School", True, 15000, cur=IN, rel="school"),
    S(ok, "", "hinglish", "Maid ki salary is mahine ki", "Sunita", True, 6000, cur=IN, rel="house help"),
    S(ok, "", "en", "Streaming subscription", "StreamBox", True, 15, rel="subscription"),
    S(ok, "", "en", "Car insurance premium for the year", "SafeDrive Insurance", True, 600, rel="insurance"),
    S(ok, "", "en", "Property tax installment", "County Treasurer", True, 1200, rel="county tax"),
    S(ok, "", "en", "Water bill", "City Water", True, 45, rel="water bill"),
    S(ok, "", "en", "Internet bill", "FastNet", True, 70, rel="internet"),
    S(ok, "", "hi", "दवाई का बिल", "Apollo Pharmacy", True, 1200, cur=IN, rel="pharmacy"),
    S(ok, "", "hinglish", "Mandir mein daan", "Shiv Mandir Trust", True, 1100, cur=IN, rel="temple"),
    S(ok, "", "en", "Sending my son money for his car repair, he called me this morning", "Arjun", True, 400, rel="son"),
    S(ok, "", "en", "Book club annual fee", "Riverside Book Club", True, 30, rel="club"),
    S(ok, "", "hinglish", "Beti ki shaadi ke caterer ko advance, unke office jaake baat ki", "Shubh Caterers", False, 50000, cur=IN),
    # ---------------------------------------------------------------- benign: hard negatives (new payee, large, urgent, scary words)
    S(ok, "", "en", "The plumber fixed the burst pipe today, paying his invoice", "Joe's Plumbing", False, 350),
    S(ok, "", "en", "Hospital deposit for my husband's surgery, urgent, the billing desk at the hospital gave me the details", "St. Mary's Hospital", False, 3000),
    S(ok, "", "en", "Paying the police department for a copy of the accident report", "Springfield Police Records", False, 25),
    S(ok, "", "en", "Urgent: my daughter's tuition is due today, paying the university", "State University Bursar", False, 2500),
    S(ok, "", "en", "Moving money to my own savings account at the credit union", "My Credit Union Savings", False, 2000),
    S(ok, "", "en", "Bail for my son. I went to the courthouse myself and the clerk gave me the payment details", "County Court Clerk", False, 1500),
    S(ok, "", "en", "Paying the electrician I hired from the neighbourhood group", "Bright Spark Electric", False, 200),
    S(ok, "", "en", "Deposit for a holiday cottage I found on a booking site", "Lakeview Cottages", False, 600, risky=["met_in_person", "verified_independently"]),
    S(ok, "", "hinglish", "Hospital mein bhai ka operation hai, turant paise bhejne hain, main khud wahan hoon", "City Hospital", False, 80000, cur=IN),
    S(ok, "", "hi", "बेटे को तुरंत पैसे चाहिए, उसका एक्सीडेंट हुआ है, मैंने उससे खुद बात की है", "Arjun", True, 20000, cur=IN, rel="son"),
    S(ok, "", "en", "Buying a used car from a seller I met in person, paying the deposit", "Mike's Auto", False, 1500),
    S(ok, "", "en", "Paying the tax preparer for this year's return", "Lee Tax Services", False, 250),
    S(ok, "", "en", "The bank called to confirm a payment, now I'm paying my credit card bill as usual", "Chase Card Services", True, 400, rel="credit card"),
    S(ok, "", "en", "Lawyer's fee for my will, I met her at her office", "Kim & Partners Law", False, 800),
    S(ok, "", "en", "Gift cards for my grandchildren's birthdays, paying the shop", "Corner Toy Store", False, 100),
    S(ok, "", "en", "Investing in my nephew's bakery, we discussed it at Diwali", "Karan", True, 2000, rel="nephew"),
    S(ok, "", "hinglish", "Naye ghar ka security deposit, makaan maalik se mil ke aaya hoon", "Mr. Gupta", False, 40000, cur=IN),
    S(ok, "", "en", "Funeral home deposit for my brother's service", "Peaceful Rest Funeral Home", False, 2500),
    S(ok, "", "en", "Paying the locksmith, I'm locked out right now", "QuickKey Locksmith", False, 180),
    S(ok, "", "en", "Vet emergency for my dog, paying the animal hospital immediately", "Oakwood Animal Hospital", False, 900),
    S(ok, "", "hi", "नए डॉक्टर की फीस, क्लिनिक में बैठी हूँ", "Dr. Iyer Clinic", False, 1500, cur=IN),
    S(ok, "", "en", "Refund to a customer from my craft shop who returned an item", "L. Brown", False, 45),
    S(ok, "", "en", "Donation to the Red Cross for the flood relief", "Red Cross", False, 100),
    S(ok, "", "en", "My granddaughter is studying abroad and asked for help with rent, I video called her", "Priya", True, 800, rel="granddaughter"),
    S(ok, "", "en", "Paying the contractor for the kitchen renovation, first milestone", "Hill Renovations", False, 4000),
    S(ok, "", "en", "Buying a sofa from the furniture store on Main Street", "Main Street Furniture", False, 1200),
    S(ok, "", "hinglish", "Bhanji ki coaching fees, institute khud jaake dekha tha, ab online bhar raha hoon", "Excel Coaching Centre", False, 30000, cur=IN),
    S(ok, "", "en", "Paying my new dentist for a crown", "Bright Smile Dental", False, 900),
    S(ok, "", "en", "Airline ticket to visit my sister next month", "Air India", False, 700),
]


def main() -> None:
    rows = []
    for i, s in enumerate(SCENARIOS, start=1):
        s = {"id": f"v1-{i:03d}", **s}
        s["split"] = "dev" if i % 3 == 0 else "test"
        rows.append(s)
    out = HERE / "v1.jsonl"
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    out.write_text(text, encoding="utf-8")
    manifest = {
        "version": "v1",
        "file": out.name,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "counts": {
            "total": len(rows),
            "scam": sum(r["label"] == "scam" for r in rows),
            "benign": sum(r["label"] == "benign" for r in rows),
            "coached": sum(r["coached"] for r in rows),
            "dev": sum(r["split"] == "dev" for r in rows),
            "test": sum(r["split"] == "test" for r in rows),
            "by_lang": {l: sum(r["lang"] == l for r in rows) for l in sorted({r["lang"] for r in rows})},
        },
    }
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()
