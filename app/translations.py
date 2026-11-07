TRANSLATIONS = {
    "en": {
        "nav_home": "Home",
        "nav_login": "Login",
        "nav_register": "Register",
        "nav_logout": "Logout",
        "nav_hi": "Hi",
        "welcome_title": "Welcome to YatraEase",
        "welcome_sub": "Book buses, stays and attractions across Andhra Pradesh and Telangana.",
        "popular_services": "Popular services",
        "footer_text": "YatraEase © 2026. A student portfolio project with simulated data.",
        "type_bus": "Bus",
        "type_hotel": "Hotel",
        "type_campsite": "Campsite",
        "type_attraction": "Attraction",
    },
    "hi": {
        "nav_home": "होम",
        "nav_login": "लॉगिन",
        "nav_register": "रजिस्टर",
        "nav_logout": "लॉगआउट",
        "nav_hi": "नमस्ते",
        "welcome_title": "YatraEase में आपका स्वागत है",
        "welcome_sub": "आंध्र प्रदेश और तेलंगाना में बस, ठहरने की जगह और घूमने के स्थान बुक करें।",
        "popular_services": "लोकप्रिय सेवाएँ",
        "footer_text": "YatraEase © 2026. सिमुलेटेड डेटा के साथ एक छात्र पोर्टफोलियो प्रोजेक्ट।",
        "type_bus": "बस",
        "type_hotel": "होटल",
        "type_campsite": "कैंपसाइट",
        "type_attraction": "आकर्षण",
    },
}

SUPPORTED_LANGUAGES = ("en", "hi")
DEFAULT_LANGUAGE = "en"


def translate(key, lang):
    language_texts = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    return language_texts.get(key, TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key))