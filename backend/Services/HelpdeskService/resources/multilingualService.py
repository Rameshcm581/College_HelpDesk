# backend/Services/HelpdeskService/resources/multilingualService.py
import re
from typing import Dict, List, Set, Tuple

# Tamil Unicode range: \u0B80 to \u0BFF
TAMIL_SCRIPT_REGEX = re.compile(r'[\u0B80-\u0BFF]')

# Transliterated Tamil (Tanglish) lexicon mapped to English concepts and Tamil script
TANGLISH_CONCEPT_MAP: Dict[str, Tuple[List[str], str]] = {
    # fees & admission
    "kattanam": (["fee", "tuition", "cost", "charge"], "கட்டணம்"),
    "katnam": (["fee", "tuition", "cost"], "கட்டணம்"),
    "panam": (["money", "fee", "deposit"], "பணம்"),
    "evvalavu": (["how much", "fee amount", "cost"], "எவ்வளவு"),
    "evalavu": (["how much", "fee amount"], "எவ்வளவு"),
    "serkai": (["admission", "enrolment"], "சேர்க்கை"),
    "katta": (["pay", "payment", "clear"], "செலுத்த"),
    "eppadi": (["how to", "procedure", "process"], "எப்படி"),
    "eppo": (["when", "last date", "deadline"], "எப்போது"),

    # hostel & living
    "viduthi": (["hostel", "mess", "caution deposit"], "விடுதி"),
    "saapadu": (["mess", "food", "dining"], "உணவு"),
    "vaippu": (["caution deposit", "security deposit"], "வைப்பு"),

    # examinations & attendance
    "thearvu": (["exam", "examination", "hall ticket"], "தேர்வு"),
    "thervu": (["exam", "examination", "hall ticket"], "தேர்வு"),
    "varugai": (["attendance", "condonation", "percentage"], "வருகை"),
    "marumathipeedu": (["revaluation", "photocopy", "script"], "மறுமதிப்பீடு"),
    "condonation": (["attendance exemption", "medical certificate", "shortage"], "விலக்கு"),
    "abaram": (["penalty", "late fee", "fine"], "அபராதம்"),

    # scholarships
    "udavithogai": (["scholarship", "financial aid", "concession"], "உதவித்தொகை"),
}

# Cross-lingual Tamil to English dictionary for bridging
TAMIL_TO_ENGLISH_MAP: Dict[str, List[str]] = {
    "கட்டணம்": ["tuition", "fee", "cost", "charge"],
    "சேர்க்கை": ["admission", "eligibility", "cutoff"],
    "விடுதி": ["hostel", "room", "mess", "warden"],
    "வைப்பு": ["caution deposit", "deposit"],
    "வைப்புத் தொகை": ["caution deposit", "security deposit"],
    "தேர்வு": ["examination", "exam", "hall ticket"],
    "வருகை": ["attendance", "75%", "condonation"],
    "மறுமதிப்பீடு": ["revaluation", "answer script"],
    "அபராதம்": ["penalty", "late fee", "fine"],
    "உதவித்தொகை": ["scholarship", "merit concession"],
    "கணினி அறிவியல்": ["computer science", "cse"],
    "கடைசி தேதி": ["last date", "deadline", "due date"],
    "முதல் தலைமுறை பட்டதாரி": ["first graduate", "first generation graduate"],
    "விளையாட்டு": ["sports", "sports quota", "gold medal", "national level"],
    "மாணவர் நலன்": ["student welfare", "room 105"],
    "சான்றிதழ்": ["certificate", "tahsildar"],
    "உணவுக்கூடம்": ["dining hall", "mess", "breakfast", "lunch", "dinner"],
    "தகுதி": ["merit", "cutoff", "185.50"],
    "வாடகை": ["room rent", "twin sharing", "single occupancy"],
    "விலக்கு": ["waiver", "concession", "exemption"],
}


class MultilingualService:
    """Provides language detection, Tamil-English cross-lingual query expansion,
    and transliterated Tamil (Tanglish) query normalization.
    """

    def detect_language(self, query: str) -> str:
        """Detects whether query is in Tamil script ('ta'), transliterated Tanglish ('ta-Latn'),
        or standard English ('en').
        """
        if TAMIL_SCRIPT_REGEX.search(query):
            return "ta"

        words = re.findall(r'[a-zA-Z]+', query.lower())
        tanglish_count = sum(1 for w in words if w in TANGLISH_CONCEPT_MAP)
        if tanglish_count >= 1:
            return "ta-Latn"

        return "en"

    def expand_query_cross_lingual(self, query: str) -> Tuple[str, List[str]]:
        """Expands a query with cross-lingual bridge keywords for both dense embedding
        and sparse keyword tsquery search.
        Returns:
            expanded_semantic_query: Enhanced string for embedding models
            keyword_tokens: List of terms for PostgreSQL full-text search
        """
        lang = self.detect_language(query)
        expanded_parts = [query.strip()]
        keyword_tokens: Set[str] = set()

        # Clean words for token extraction
        raw_tokens = re.findall(r'[a-zA-Z0-9_\u0B80-\u0BFF]+', query.lower())
        for t in raw_tokens:
            if len(t) >= 2:
                keyword_tokens.add(t)

        # 1. Transliterated Tamil (Tanglish) Expansion
        if lang == "ta-Latn":
            for word in raw_tokens:
                if word in TANGLISH_CONCEPT_MAP:
                    en_synonyms, ta_term = TANGLISH_CONCEPT_MAP[word]
                    expanded_parts.extend(en_synonyms)
                    expanded_parts.append(ta_term)
                    keyword_tokens.update(en_synonyms)
                    keyword_tokens.add(ta_term)

        # 2. Pure Tamil Script Expansion
        elif lang == "ta":
            for ta_term, en_synonyms in TAMIL_TO_ENGLISH_MAP.items():
                if ta_term in query:
                    expanded_parts.extend(en_synonyms)
                    keyword_tokens.update(en_synonyms)

        # 3. English Query Expansion to Tamil terms (for querying Tamil documents)
        elif lang == "en":
            for ta_term, en_synonyms in TAMIL_TO_ENGLISH_MAP.items():
                if any(syn in query.lower() for syn in en_synonyms):
                    expanded_parts.append(ta_term)
                    keyword_tokens.add(ta_term)

        expanded_semantic_query = " | ".join(dict.fromkeys(expanded_parts))
        return expanded_semantic_query, list(keyword_tokens)

    def build_tsquery_string(self, keyword_tokens: List[str]) -> str:
        """Constructs a safe, syntax-valid PostgreSQL plain tsquery string using OR / AND logic."""
        # Filter out common stop words
        stop_words = {
            "what", "is", "the", "for", "and", "or", "to", "in", "of", "a", "an",
            "how", "much", "does", "can", "you", "tell", "me", "about", "please",
            "என்பது", "என்ன", "எங்கு", "எப்படி", "எவ்வளவு"
        }
        filtered = [t for t in keyword_tokens if t.lower() not in stop_words and len(t) >= 2]
        if not filtered:
            return ""

        # Join keywords with logical 'or' so websearch_to_tsquery handles terms with OR logic
        # Sanitize single quotes and punctuation
        sanitized = [re.sub(r"[^\w\u0B80-\u0BFF]", "", t) for t in filtered if t]
        return " or ".join(s for s in sanitized if s)


multilingual_service = MultilingualService()
