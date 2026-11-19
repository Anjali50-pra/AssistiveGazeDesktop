"""
nlp/languages.py
Words, menus and sentence rules for English, Hindi and Telugu.
Hindi and Telugu are naturally Subject-Object-Verb (SOV). English is naturally SVO.

ENGLISH_ORDER:
  "SVO" -> "I want to eat dal roti."   (grammatical English, recommended)
  "SOV" -> "I dal roti want to eat."   (literal SOV, only if the doctor insists)
"""

ENGLISH_ORDER = "SVO"

# 3 x 2 main menu, in grid order (row 0: first three, row 1: last three)
MENU_ORDER = ["eat", "water", "go", "pain", "help", "yesno"]

LANG_CODES = ["en", "hi", "te"]          # order of the cards on the language page

# item = (key, card label, phrase used inside the sentence[, verb override])
# An empty phrase ("") simply leaves the object out of the sentence.
LANG = {
    # ------------------------------------------------------------------ HINDI (SOV)
    "hi": {
        "native": "हिन्दी",
        "order": "SOV",
        "end": "",
        "ui": {
            "title": "AAC Assistive Gaze Interface",
            "choose": "भाषा चुनें",
            "back": "वापस",
            "next": "अगला ›",
            "output_back": "वापस (BACK)",
            "language": "भाषा",
            "back_lang": "वापस / भाषा",
        },
        "menu": {"eat": "खाना", "water": "पानी", "go": "जाना है",
                 "pain": "दर्द", "help": "मदद", "yesno": "हाँ / नहीं / भाषा"},
        "cats": {
            "eat": {"s": "मुझे", "v": "चाहिए", "items": [
                ("dal_roti", "दाल रोटी", "खाने में दाल रोटी"),
                ("rice_curry", "चावल सब्ज़ी", "खाने में चावल सब्ज़ी"),
                ("breakfast", "नाश्ता", "नाश्ता"),
                ("biscuits", "बिस्कुट", "बिस्कुट"),
                ("dal_rice", "दाल भात", "खाने में दाल भात"),
                ("other", "कुछ और", "खाने में कुछ और"),
            ]},
            "go": {"s": "मुझे", "v": "जाना है", "items": [
                ("room", "कमरे में", "कमरे में"),
                ("washroom", "वॉशरूम", "वॉशरूम"),
                ("bed", "बिस्तर पर", "बिस्तर पर"),
                ("home", "घर", "घर"),
                ("outside", "बाहर", "बाहर"),
                ("hospital", "अस्पताल", "अस्पताल"),
                ("garden", "बगीचे में", "बगीचे में"),
            ]},
            "pain": {"s": "मुझे", "v": "दर्द हो रहा है", "items": [
                ("head", "सर में", "सर में"),
                ("stomach", "पेट में", "पेट में"),
                ("chest", "छाती में", "छाती में"),
                ("hand", "हाथ में", "हाथ में"),
                ("legs", "पैरों में", "पैरों में"),
                ("back", "पीठ में", "पीठ में"),
                ("somewhere", "कहीं", ""),
            ]},
        },
        "direct": {
            "water": {"s": "मुझे", "o": "पानी", "v": "चाहिए"},
            "help": {"s": "मुझे", "o": "मदद", "v": "चाहिए"},
            "yes": {"word": "हाँ"},
            "no": {"word": "नहीं"},
        },
    },
    # ----------------------------------------------------------------- TELUGU (SOV)
    "te": {
        "native": "తెలుగు",
        "order": "SOV",
        "end": "",
        "ui": {
            "title": "AAC Assistive Gaze Interface",
            "choose": "భాషను ఎంచుకోండి",
            "back": "వెనుకకు",
            "next": "తదుపరి ›",
            "output_back": "వెనుకకు (BACK)",
            "language": "భాష",
            "back_lang": "వెనుకకు / భాష",
        },
        "menu": {"eat": "ఆహారం", "water": "నీళ్ళు", "go": "వెళ్ళాలి",
                 "pain": "నొప్పి", "help": "సహాయం", "yesno": "అవును / లేదు / భాష"},
        "cats": {
            "eat": {"s": "నాకు", "v": "కావాలి", "items": [
                ("dal", "పప్పు", "తినడానికి పప్పు"),
                ("rice", "అన్నం", "తినడానికి అన్నం"),
                ("curry", "కూర", "తినడానికి కూర"),
                ("breakfast", "టిఫిన్", "తినడానికి టిఫిన్"),
                ("biscuits", "బిస్కెట్లు", "బిస్కెట్లు"),
                ("other", "ఇంకేదైనా", "తినడానికి ఇంకేదైనా"),
            ]},
            "go": {"s": "నేను", "v": "వెళ్ళాలి", "items": [
                ("room", "గదిలోకి", "గదిలోకి"),
                ("washroom", "బాత్రూమ్‌కి", "బాత్రూమ్‌కి"),
                ("bed", "మంచం మీదకు", "మంచం మీదకు"),
                ("home", "ఇంటికి", "ఇంటికి"),
                ("outside", "బయటకు", "బయటకు"),
                ("hospital", "ఆసుపత్రికి", "ఆసుపత్రికి"),
                ("garden", "తోటలోకి", "తోటలోకి"),
            ]},
            "pain": {"s": "నాకు", "v": "నొప్పిగా ఉంది", "items": [
                ("head", "తలలో", "తలలో"),
                ("stomach", "కడుపులో", "కడుపులో"),
                ("chest", "ఛాతీలో", "ఛాతీలో"),
                ("hand", "చేతిలో", "చేతిలో"),
                ("legs", "కాళ్ళలో", "కాళ్ళలో"),
                ("back", "వీపులో", "వీపులో"),
                ("somewhere", "ఎక్కడో", "ఎక్కడో"),
            ]},
        },
        "direct": {
            "water": {"s": "నాకు", "o": "నీళ్ళు", "v": "కావాలి"},
            "help": {"s": "నాకు", "o": "సహాయం", "v": "కావాలి"},
            "yes": {"word": "అవును"},
            "no": {"word": "లేదు"},
        },
    },
    # ---------------------------------------------------------------- ENGLISH (SVO)
    "en": {
        "native": "English",
        "order": "SVO",                  # ENGLISH_ORDER above is what is actually used
        "end": ".",
        "ui": {
            "title": "AAC Assistive Gaze Interface",
            "choose": "Choose language",
            "back": "Back",
            "next": "Next ›",
            "output_back": "BACK",
            "language": "Language",
            "back_lang": "Back / Language",
        },
        "menu": {"eat": "Food", "water": "Water", "go": "Go",
                 "pain": "Pain", "help": "Help", "yesno": "Yes / No / Language"},
        "cats": {
            "eat": {"s": "I", "v": "want to eat", "items": [
                ("dal_roti", "Dal roti", "dal roti"),
                ("rice_curry", "Rice curry", "rice and curry"),
                ("breakfast", "Breakfast", "breakfast", "want"),
                ("biscuits", "Biscuits", "biscuits", "want"),
                ("dal_rice", "Dal rice", "dal rice"),
                ("other", "Something else", "something else"),
            ]},
            "go": {"s": "I", "v": "want to go", "items": [
                ("room", "Room", "to the room"),
                ("washroom", "Washroom", "to the washroom"),
                ("bed", "Bed", "to the bed"),
                ("home", "Home", "home"),
                ("outside", "Outside", "outside"),
                ("hospital", "Hospital", "to the hospital"),
                ("garden", "Garden", "to the garden"),
            ]},
            "pain": {"s": "I", "v": "have pain", "items": [
                ("head", "Head", "in my head"),
                ("stomach", "Stomach", "in my stomach"),
                ("chest", "Chest", "in my chest"),
                ("hand", "Hand", "in my hand"),
                ("legs", "Legs", "in my legs"),
                ("back", "Back", "in my back"),
                ("somewhere", "Somewhere", "somewhere"),
            ]},
        },
        "direct": {
            "water": {"s": "I", "o": "water", "v": "want"},
            "help": {"s": "I", "o": "help", "v": "need"},
            "yes": {"word": "Yes"},
            "no": {"word": "No"},
        },
    },
}


def order_for(lang):
    return ENGLISH_ORDER if lang == "en" else LANG[lang]["order"]


def ui(lang, key):
    return LANG[lang]["ui"][key]


def native_name(lang):
    return LANG[lang]["native"]


def menu_cards(lang):
    """[(key, label), ...] in grid order for the 3 x 2 main menu."""
    m = LANG[lang]["menu"]
    return [(k, m[k]) for k in MENU_ORDER]


def is_category(key):
    return key in ("eat", "go", "pain")


def sub_items(lang, cat):
    """[(item_key, card_label), ...] for a sub-menu."""
    return [(it[0], it[1]) for it in LANG[lang]["cats"][cat]["items"]]


def build_sentence(lang, key, item_key=None):
    """
    key      : 'eat' | 'go' | 'pain' | 'water' | 'help' | 'yes' | 'no'
    item_key : sub-menu key for eat / go / pain
    Returns the sentence in the word order of that language.
    """
    data = LANG[lang]
    end = data["end"]

    if key in data["direct"]:
        d = data["direct"][key]
        if "word" in d:
            return d["word"]
        s, o, v = d["s"], d["o"], d["v"]
    else:
        cat = data["cats"][key]
        item = next(it for it in cat["items"] if it[0] == item_key)
        s, o = cat["s"], item[2]
        v = item[3] if len(item) > 3 else cat["v"]

    parts = [s, o, v] if order_for(lang) == "SOV" else [s, v, o]
    text = " ".join(p for p in parts if p)
    if lang == "en":
        text = text[0].upper() + text[1:]
    return text + end