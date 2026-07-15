import re
import unicodedata
from html import unescape


TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
TAG_RE = re.compile(r"<[^>]+>")
NON_CONTENT_RE = re.compile(r"<(script|style|noscript|svg)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
SPACE_RE = re.compile(r"\s+")


# Common road-law concepts in BIMSTEC languages. Retrieval remains useful
# before the small LLM is warm and does not need a translation API.
QUERY_ALIASES: dict[str, tuple[str, ...]] = {
    "overspeeding": (
        "speed",
        "speeding",
        "overspeed",
        "speed limit",
        "ความเร็ว",
        "ขับรถเร็ว",
        "গতি",
        "দ্রুতগতি",
        "गति",
        "तीव्र गति",
        "වේගය",
        "အမြန်နှုန်း",
    ),
    "no_helmet": (
        "helmet",
        "no helmet",
        "motorcycle helmet",
        "หมวกกันน็อก",
        "หมวกนิรภัย",
        "হেলমেট",
        "हेलमेट",
        "हेल्मेट",
        "හිස්වැසුම",
        "ဦးထုပ်",
    ),
    "no_seatbelt": (
        "seat belt",
        "seatbelt",
        "safety belt",
        "เข็มขัดนิรภัย",
        "সিটবেল্ট",
        "सिट बेल्ट",
        "सीट बेल्ट",
        "ආසන පටිය",
        "ထိုင်ခုံခါးပတ်",
    ),
    "drink_driving": (
        "drink driving",
        "drunk driving",
        "driving under influence",
        "alcohol",
        "เมาแล้วขับ",
        "แอลกอฮอล์",
        "মদ্যপ গাড়ি চালানো",
        "मादक पदार्थ सेवन गरी सवारी",
        "नशे में गाड़ी",
        "බීමත්ව රිය පැදවීම",
        "အရက်မူးမောင်း",
    ),
    "no_license": (
        "license",
        "licence",
        "driving license",
        "driver licence",
        "ใบขับขี่",
        "ড্রাইভিং লাইসেন্স",
        "सवारी चालक अनुमति पत्र",
        "ड्राइविंग लाइसेंस",
        "රියදුරු බලපත්‍රය",
        "ယာဉ်မောင်းလိုင်စင်",
    ),
    "mobile_phone": (
        "mobile phone",
        "cell phone",
        "handheld phone",
        "distracted driving",
        "โทรศัพท์",
        "মোবাইল ফোন",
        "मोबाइल फोन",
        "ජංගම දුරකථනය",
        "မိုဘိုင်းဖုန်း",
    ),
    "no_insurance": ("insurance", "motor insurance", "ประกันภัย", "বীমা", "बीमा", "රක්ෂණය", "အာမခံ"),
    "no_registration": (
        "registration",
        "number plate",
        "ทะเบียนรถ",
        "নিবন্ধন",
        "दर्ता",
        "पंजीकरण",
        "ලියාපදිංචිය",
        "မှတ်ပုံတင်",
    ),
}


def normalize_space(value: str) -> str:
    return SPACE_RE.sub(" ", value or "").strip()


def tokenize(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    return TOKEN_RE.findall(normalized)


def expand_query(value: str) -> tuple[list[str], set[str]]:
    """Return Unicode tokens plus canonical traffic-law concepts."""

    normalized = unicodedata.normalize("NFKC", value or "").casefold()
    concepts: set[str] = set()
    expanded = list(tokenize(normalized))
    for concept, aliases in QUERY_ALIASES.items():
        if any(alias.casefold() in normalized for alias in aliases):
            concepts.add(concept)
            expanded.extend(tokenize(concept.replace("_", " ")))
            for alias in aliases:
                if alias.isascii():
                    expanded.extend(tokenize(alias))
    return list(dict.fromkeys(expanded)), concepts


def strip_html(value: str) -> str:
    text = NON_CONTENT_RE.sub(" ", value or "")
    text = COMMENT_RE.sub(" ", text)
    text = TAG_RE.sub(" ", text)
    return normalize_space(unescape(text))


def split_chunks(text: str, max_chars: int = 1200, overlap: int = 140) -> list[str]:
    clean = normalize_space(text)
    if len(clean) <= max_chars:
        return [clean] if clean else []

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        cut = clean.rfind(". ", start, end)
        if cut > start + int(max_chars * 0.55):
            end = cut + 1
        chunk = normalize_space(clean[start:end])
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = max(0, end - overlap)
    return chunks
