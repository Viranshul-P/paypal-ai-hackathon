"""Synthetic training data for the scam-language classifier.

Built from templates and phrase lists, written separately from the hand-written benchmark in
eval/scenarios/. The research question is whether a model trained on generic scam-script
patterns generalises to independently written requests, so nothing here copies a benchmark
sentence (eval/check_leakage.py measures overlap).

Deterministic: the same seed gives the same data.
"""

from __future__ import annotations

import random

# ------------------------------------------------------------------ English scam pieces
AUTHORITIES = [
    "the bank fraud team", "a bank manager", "someone from the RBI", "a police officer", "a CBI officer",
    "a customs officer", "an income tax officer", "an IRS agent", "a FedEx agent", "the courier company",
    "Microsoft support", "Amazon customer care", "the cyber crime cell", "a TRAI officer",
    "the Social Security office", "the electricity board", "the card security department", "a narcotics officer",
]
CONTACT = [
    "called and said", "told me on the phone", "is on the phone and says", "sent a message saying",
    "is on a video call and says", "called from an unknown number and said", "keeps calling and says",
]
SAFE_CLAIM = [
    "my account has been hacked", "my account will be frozen tonight", "there is fraud on my card",
    "my savings are at risk", "someone is stealing from my account", "my KYC has expired",
]
SAFE_ASK = [
    "I have to move my money to a safe account", "I must transfer my savings to a secure account",
    "I need to send my balance to a protected account", "I should shift my funds to a new account for safety",
    "I must move everything to a temporary account until it is fixed",
]
ARREST_CLAIM = [
    "a parcel in my name had drugs", "my Aadhaar was used for money laundering", "there is a case against me",
    "a warrant has been issued in my name", "my number was used in a crime", "my bank account is linked to illegal activity",
]
ARREST_ASK = [
    "I must pay a verification deposit", "I have to pay a fine or I will be arrested",
    "I need to pay to clear my name", "I must transfer money for an investigation check",
    "I will be under digital arrest unless I pay", "I should pay a security amount that will be refunded",
]
RELATIVES = ["my grandson", "my granddaughter", "my nephew", "my niece", "my son", "my daughter"]
TROUBLE = ["is in jail", "had a car accident", "is stuck abroad", "is in hospital", "was arrested", "lost his wallet overseas"]
FAMILY_TWIST = [
    "and is calling from a new number", "and the lawyer called me", "and needs bail money",
    "and a friend of his is collecting the money", "and the officer said to pay a bond",
]
TECH_CLAIM = [
    "my computer has a virus", "they installed AnyDesk to help me", "they refunded too much money by mistake",
    "my bank app has been hacked", "my router is sending spam", "my subscription will auto renew for a big amount",
]
TECH_ASK = [
    "I need to pay for the repair", "I must send back the extra refund", "I should buy gift cards to fix it",
    "I have to pay for a protection plan", "I need to pay to cancel the renewal",
]
ROMANCE_WHO = [
    "my friend I met online", "my fiance who works on an oil rig", "a soldier I met on Facebook",
    "the man from the dating app", "a doctor I chat with on Instagram", "my online boyfriend",
]
ROMANCE_NEED = [
    "needs money to clear customs", "needs a flight ticket to visit me", "needs money for a hospital bill",
    "needs help with a visa fee", "needs money to release his gold shipment",
]
PRIZE_WIN = ["I won a lottery", "I won a car in a lucky draw", "I won a prize", "I am the winner of a sweepstakes", "I got an inheritance from abroad"]
PRIZE_ASK = ["I need to pay a processing fee", "I must pay the tax first", "I have to pay a release fee", "I should pay the delivery charge to get it"]
INVEST_WHO = ["the trading group", "the crypto platform", "the WhatsApp investment group", "a Telegram trading coach", "the stock tips channel"]
INVEST_ASK = [
    "guarantees high returns every day", "shows a big profit but I need to pay a withdrawal fee",
    "says I must deposit more to unlock my account", "promises to double my money", "needs a tax payment before I can withdraw",
]
REFUND = [
    "someone sent me money by mistake and asked me to return the extra", "the company overpaid me and wants the difference back",
    "the supplier emailed that their bank details changed", "I got a text that my parcel needs a redelivery fee",
    "a message said I have an unpaid toll fine",
]
JOB = [
    "the part time job asks for a deposit to unlock my earnings", "the task job needs a registration fee",
    "rating hotels online pays but I need to top up first", "the work from home company wants a training fee",
    "the YouTube liking job needs a deposit to continue",
]
URGENCY = ["", "", "today", "right now", "within one hour", "immediately", "before tonight"]
SECRECY = ["", "", "", "and not to tell anyone", "and to keep it secret", "and not to tell my family", "and not to tell the bank"]
METHOD = ["", "", "", "in gift cards", "in bitcoin", "by crypto", "with Google Play cards"]

# ------------------------------------------------------------------ Hinglish / Hindi scam pieces
HL_AUTH = ["bank wale", "police wale", "CBI officer", "customs wale", "courier company wale", "RBI se koi", "cyber cell wale", "bijli vibhag wale"]
HL_CLAIM = [
    "account hack ho gaya hai", "account band ho jayega", "parcel mein drugs mile hain", "mere naam pe case hai",
    "money laundering ka case hai", "number band ho jayega", "KYC expire ho gaya hai", "arrest warrant nikla hai",
]
HL_ASK = [
    "paise safe account mein bhejne honge", "verification ke liye paise bhejo", "fine bharna padega", "deposit karna hoga",
    "is account mein transfer karo", "gift card lena hoga", "security amount bhejna hai jo wapas milega",
]
HL_PRESSURE = ["", "abhi", "turant", "jaldi", "kisi ko mat batana", "video call pe hai", "phone pe hai abhi bhi", "aaj hi"]
HL_OTHER = [
    "lottery jeeti hai, pehle tax bharna hai", "online dost ko visa fee chahiye, hum kabhi mile nahi",
    "trading app mein profit hai, withdraw fee bharni hai", "part time job ke liye deposit chahiye",
    "beta naye number se bol raha hai paise bhejo, kisi ko mat batana", "TeamViewer install karwaya, refund ke liye charge dena hai",
    "galti se paise aa gaye, wapas bhejne ko bola", "paise double karne wali scheme hai",
]
HI_AUTH = ["बैंक वालों", "पुलिस वालों", "सीबीआई अफसर", "कस्टम अधिकारी", "कूरियर कंपनी वालों", "साइबर सेल वालों"]
HI_CLAIM = ["खाता हैक हो गया है", "मेरे नाम पर केस है", "पार्सल में ड्रग्स मिले हैं", "खाता बंद हो जाएगा", "गिरफ्तारी का वारंट है"]
HI_ASK = ["पैसे सुरक्षित खाते में भेजने हैं", "जुर्माना भरना होगा", "जांच के लिए पैसे भेजने हैं", "जमा राशि भेजनी होगी"]
HI_PRESSURE = ["", "अभी", "तुरंत", "किसी को मत बताना", "वीडियो कॉल पर हैं", "आज ही"]
HI_OTHER = [
    "मुझे इनाम मिला है, पहले फीस भरनी है", "ऑनलाइन दोस्त को विदेश से आने के लिए पैसे चाहिए",
    "पैसे दोगुने करने की योजना में पैसे लगाने हैं", "नौकरी के लिए पहले जमा राशि मांगी है",
    "पोता नए नंबर से पैसे मांग रहा है, किसी को न बताने को कहा", "फ़ोन पर किसी ने स्क्रीन शेयर करवाई और मरम्मत के पैसे मांगे",
]

# ------------------------------------------------------------------ benign pieces
BENIGN_REL = ["grandson", "granddaughter", "son", "daughter", "nephew", "niece", "sister", "brother", "friend", "neighbour"]
BENIGN_ITEM = ["college books", "school fees", "birthday", "wedding gift", "train ticket", "new shoes", "laptop repair", "rent help", "medicine", "exam fees"]
BILLS = ["electricity", "water", "gas", "phone", "internet", "credit card", "insurance", "property tax", "cable TV", "maintenance"]
SERVICES = ["gardener", "maid", "driver", "cook", "tutor", "yoga class", "newspaper", "milkman", "physiotherapist", "dog walker"]
SHOPS = ["the pharmacy", "the grocery store", "the furniture shop", "the hardware store", "the bakery", "the bookshop", "the tailor", "the optician"]
TRADES = ["plumber", "electrician", "carpenter", "painter", "locksmith", "mechanic", "AC repair man", "roofer"]
PLACES = ["the hospital", "the clinic", "the dentist", "the vet", "the school", "the university", "the temple", "the church", "the funeral home", "the court office"]
BENIGN_TEMPLATES = [
    "{rel}'s {item}", "money for my {rel}'s {item}", "sending my {rel} money for {item}", "{bill} bill for this month",
    "paying the {bill} bill", "monthly payment for the {svc}", "paying the {svc} for this month", "paying {shop} for my order",
    "bought things at {shop}", "paying the {trade} who fixed it today", "the {trade} finished the work, paying his bill",
    "deposit at {place}", "fees for {place}", "donation to {place}", "paying back my {rel} for dinner", "gift for my {rel}",
    "my share of the holiday cost to my {rel}", "advance for the {trade}, he came to the house", "{place} bill, I am here now",
    "{item} for my {rel}", "helping my {rel} with {item}", "{bill} payment, same as every month", "{bill} bill is due on Friday",
    "the {svc}'s wages", "tip for the {svc}", "paying {shop}, I picked it up myself", "order from {shop}", "{trade} came this morning",
    "half advance to the {trade} for next week", "{place} fees for this term", "appointment fee at {place}",
    "my {rel} paid for my ticket, paying back", "splitting the dinner bill with my {rel}", "contribution for my {rel}'s farewell party",
    "annual fee for {place}", "{rel} needs it for {item}, we talked at home", "pocket money for my {rel}",
]
# Benign requests that use words scammers also use: the classifier must learn context, not keywords.
HARD_BENIGN = [
    "fee to the police station for my lost phone complaint copy", "fee for police verification for my passport",
    "hospital deposit for the operation, I am at the billing desk", "urgent payment to the hospital for my husband",
    "buying gift cards for my grandchildren from the shop", "gift card for my niece's birthday from the store",
    "moving money to my own savings account at another bank", "transferring to my own fixed deposit",
    "bail for my son, I am at the courthouse with the clerk", "advocate's fee for the property papers, I went to his chamber",
    "my granddaughter on video call asked for help with her rent", "my son called me this morning about his car repair",
    "tax payment to the income tax department through the official website", "paying the customs duty on my parcel at the post office",
    "investment in my nephew's shop, we discussed it at home", "the bank manager helped me open a fixed deposit at the branch",
    "refund to a customer of my shop who returned an item", "paying the courier company for sending a parcel",
    "urgent: school fees due today", "locksmith fee, I am locked out right now", "vet emergency for my dog, paying immediately",
    "advance rent for the new flat, I saw it in person", "paying the electricity board at their office counter",
    "subscription renewal for my newspaper", "insurance premium, the agent visited the house",
    "returning money to a buyer for a cancelled order", "money back to my tenant for the extra rent he paid",
    "giving back the deposit to the guest who stayed at our house", "refund for the tuition class my student missed",
    "my shop customer paid twice so I am returning one payment", "sending back the money my brother lent me last month",
    "paying my neighbour back, she paid my bill while I was away", "returning the advance to the painter, the job was cancelled",
]
HL_BENIGN = [
    "{rel_hl} ko {purpose_hl} ke liye", "{bill_hl} ka bill", "sabzi wale ka hisaab", "driver ki tankhwah", "gurudwara mein seva ke liye",
    "dawai ke paise", "bachchon ki school fees", "kirana dukaan ka bill", "{rel_hl} ki shaadi ka gift",
    "hospital mein operation ka deposit, main wahan hoon", "naye ghar ka security deposit, makaan maalik se mil liya",
    "{rel_hl} ne subah phone kiya tha, uski fees", "bijli ka bill office jaake bhara", "coaching ki fees",
    "{rel_hl} ke {purpose_hl} ke paise", "is mahine ka {bill_hl} bill", "{rel_hl} ko bheja {purpose_hl} ke liye",
    "{bill_hl} ka bill online bhar raha hoon", "{rel_hl} ka birthday gift", "dukaan wale ka udhaar chukana hai",
    "{rel_hl} ki {purpose_hl} ke liye ghar pe baat hui thi",
]
HL_REL = ["bete", "beti", "pote", "poti", "bhai", "behen", "bahu", "dost"]
HL_PURPOSE = ["kitaabon", "fees", "ghar ke kharche", "dawai", "ticket", "kapdon", "phone repair"]
HL_BILL = ["bijli", "paani", "gas", "phone", "internet", "society maintenance"]
HI_REL = ["बेटे", "बेटी", "पोते", "पोती", "भाई", "बहन", "बहू", "दोस्त"]
HI_PURPOSE = ["किताबों", "फीस", "घर खर्च", "दवाई", "टिकट", "कपड़ों", "इलाज"]
HI_BILL = ["बिजली", "पानी", "गैस", "फ़ोन", "इंटरनेट", "मेंटेनेंस"]
HI_TEMPLATES = ["{rel} को {purpose} के लिए पैसे", "{bill} का बिल", "{rel} की {purpose} के पैसे", "इस महीने का {bill} बिल", "{rel} के जन्मदिन का तोहफ़ा"]
HI_BENIGN = [
    "पानी का बिल भरना है", "बेटे को किताबों के लिए पैसे", "मंदिर में दान",
    "डॉक्टर की फीस, क्लिनिक में हूँ", "बेटी को घर खर्च के लिए", "दूध वाले का हिसाब", "अस्पताल में जमा राशि, मैं वहीं हूँ",
    "नौकरानी की तनख्वाह", "भाई की शादी का तोहफ़ा",
]

SCAM_TYPES = (
    "bank_safe_account", "digital_arrest_or_government", "family_emergency", "tech_support", "romance",
    "prize_or_lottery", "investment_or_crypto", "fake_invoice_or_refund", "job_or_task",
)


def _join(*parts: str) -> str:
    return " ".join(p for p in parts if p).replace(" ,", ",").strip()


def _scam_en(rng: random.Random, kind: str) -> str:
    c = rng.choice
    if kind == "bank_safe_account":
        s = _join(c(AUTHORITIES[:3] + AUTHORITIES[16:17]).capitalize(), c(CONTACT), c(SAFE_CLAIM) + ",", c(SAFE_ASK), c(URGENCY), c(SECRECY))
    elif kind == "digital_arrest_or_government":
        s = _join(c(AUTHORITIES[3:10] + AUTHORITIES[12:15] + AUTHORITIES[17:]).capitalize(), c(CONTACT), c(ARREST_CLAIM) + ",", c(ARREST_ASK), c(URGENCY), c(SECRECY))
    elif kind == "family_emergency":
        s = _join(c(RELATIVES).capitalize(), c(TROUBLE), c(FAMILY_TWIST) + ",", "I need to send money", c(URGENCY), c(SECRECY), c(METHOD))
    elif kind == "tech_support":
        s = _join(c(AUTHORITIES[10:12]).capitalize(), c(CONTACT), c(TECH_CLAIM) + ",", c(TECH_ASK), c(URGENCY), c(METHOD))
    elif kind == "romance":
        s = _join(c(ROMANCE_WHO).capitalize(), c(ROMANCE_NEED), c(["", "", "but we have never met", "and I trust him", "and asked me to keep it between us"]))
    elif kind == "prize_or_lottery":
        s = _join(c(PRIZE_WIN).capitalize() + ",", c(PRIZE_ASK), c(URGENCY), c(SECRECY))
    elif kind == "investment_or_crypto":
        s = _join(c(INVEST_WHO).capitalize(), c(INVEST_ASK), c(METHOD))
    elif kind == "fake_invoice_or_refund":
        s = _join(c(REFUND).capitalize(), c(URGENCY))
    else:
        s = _join(c(JOB).capitalize(), c(URGENCY))
    return s


def _scam_hl(rng: random.Random) -> tuple[str, str]:
    c = rng.choice
    if rng.random() < 0.6:
        return _join(c(HL_AUTH), "ka call aaya,", c(HL_CLAIM) + ",", c(HL_ASK), c(HL_PRESSURE)), "digital_arrest_or_government"
    return _join(c(HL_OTHER), c(HL_PRESSURE)), "other"


def _scam_hi(rng: random.Random) -> tuple[str, str]:
    c = rng.choice
    if rng.random() < 0.6:
        return _join(c(HI_AUTH), "ने कहा", c(HI_CLAIM) + ",", c(HI_ASK), c(HI_PRESSURE)), "digital_arrest_or_government"
    return _join(c(HI_OTHER), c(HI_PRESSURE)), "other"


def _benign_en(rng: random.Random) -> str:
    c = rng.choice
    if rng.random() < 0.25:
        return c(HARD_BENIGN)
    return c(BENIGN_TEMPLATES).format(rel=c(BENIGN_REL), item=c(BENIGN_ITEM), bill=c(BILLS), svc=c(SERVICES), shop=c(SHOPS), trade=c(TRADES), place=c(PLACES))


def _benign_hl(rng: random.Random) -> str:
    c = rng.choice
    return c(HL_BENIGN).format(rel_hl=c(HL_REL), purpose_hl=c(HL_PURPOSE), bill_hl=c(HL_BILL))


def generate(n_per_class: int = 1500, seed: int = 7) -> list[dict]:
    """Return [{"text", "label": 1 scam / 0 benign, "scam_type", "lang"}], deduplicated."""
    rng = random.Random(seed)
    rows: list[dict] = []
    seen: set[str] = set()

    def add(text: str, label: int, scam_type: str, lang: str) -> None:
        key = text.lower().strip()
        if key and key not in seen:
            seen.add(key)
            rows.append({"text": text, "label": label, "scam_type": scam_type, "lang": lang})

    attempts = 0
    while sum(r["label"] == 1 for r in rows) < n_per_class and attempts < n_per_class * 20:
        attempts += 1
        r = rng.random()
        if r < 0.70:
            kind = rng.choice(SCAM_TYPES)
            add(_scam_en(rng, kind), 1, kind, "en")
        elif r < 0.88:
            text, kind = _scam_hl(rng)
            add(text, 1, kind, "hinglish")
        else:
            text, kind = _scam_hi(rng)
            add(text, 1, kind, "hi")
    attempts = 0
    while sum(r["label"] == 0 for r in rows) < n_per_class and attempts < n_per_class * 20:
        attempts += 1
        r = rng.random()
        if r < 0.72:
            add(_benign_en(rng), 0, "none", "en")
        elif r < 0.90:
            add(_benign_hl(rng), 0, "none", "hinglish")
        elif rng.random() < 0.4:
            add(rng.choice(HI_BENIGN), 0, "none", "hi")
        else:
            add(rng.choice(HI_TEMPLATES).format(rel=rng.choice(HI_REL), purpose=rng.choice(HI_PURPOSE), bill=rng.choice(HI_BILL)), 0, "none", "hi")
    rng.shuffle(rows)
    return rows


def decontaminate(rows: list[dict], reference_texts: list[str], threshold: float = 0.8) -> tuple[list[dict], int]:
    """Drop training rows whose character n-gram cosine similarity to any reference text is >= threshold.

    Used to keep the benchmark's wording out of training, so evaluation measures generalisation.
    """
    if not reference_texts:
        return rows, 0
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [r["text"] for r in rows]
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), lowercase=True).fit(texts + reference_texts)
    sims = cosine_similarity(vec.transform(texts), vec.transform(reference_texts)).max(axis=1)
    kept = [r for r, sim in zip(rows, sims) if sim < threshold]
    return kept, len(rows) - len(kept)
