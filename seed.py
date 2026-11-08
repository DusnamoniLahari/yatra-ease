import os
from datetime import date, timedelta
from app import create_app, db
from app.models import User, Service, Availability

app = create_app()

# type, English name, Hindi name, English description, Hindi description,
# location, price in INR, time slots, capacity per slot
SERVICES = [
    ("bus", "Hyderabad to Tirupati AC Sleeper Bus", "हैदराबाद से तिरुपति एसी स्लीपर बस",
     "Overnight AC sleeper bus with comfortable berths.",
     "आरामदायक बर्थ वाली रात की एसी स्लीपर बस।",
     "Hyderabad to Tirupati", 1200, ["Night 21:00"], 40),

    ("bus", "Visakhapatnam to Araku Valley Bus", "विशाखापत्तनम से अराकू घाटी बस",
     "Scenic ghat road journey through the Eastern Ghats.",
     "पूर्वी घाट के सुंदर रास्ते से होकर यात्रा।",
     "Visakhapatnam to Araku Valley", 250, ["Morning 07:00", "Afternoon 13:00"], 45),

    ("bus", "Vijayawada to Visakhapatnam Express", "विजयवाड़ा से विशाखापत्तनम एक्सप्रेस बस",
     "Comfortable express service along the coastal highway.",
     "तटीय राजमार्ग पर आरामदायक एक्सप्रेस सेवा।",
     "Vijayawada to Visakhapatnam", 650, ["Morning 06:30", "Evening 18:00"], 40),

    ("hotel", "Tirupati Pilgrim Comfort Stay", "तिरुपति तीर्थयात्री कम्फर्ट स्टे",
     "Clean AC rooms close to the temple town centre. Price per room per night.",
     "मंदिर नगरी के केंद्र के पास साफ-सुथरे एसी कमरे। कीमत प्रति कमरा प्रति रात।",
     "Tirupati", 2200, ["Check-in 12:00"], 12),

    ("hotel", "Hyderabad Heritage Boutique Hotel", "हैदराबाद हेरिटेज बुटीक होटल",
     "Boutique rooms near Charminar with local Hyderabadi dining. Price per room per night.",
     "चारमीनार के पास बुटीक कमरे, हैदराबादी भोजन के साथ। कीमत प्रति कमरा प्रति रात।",
     "Hyderabad", 3500, ["Check-in 12:00"], 10),

    ("campsite", "Araku Valley Hill Camp", "अराकू घाटी हिल कैंप",
     "Tent stay with bonfire and valley views. Price per tent per night.",
     "अलाव और घाटी के नज़ारों के साथ टेंट में ठहरना। कीमत प्रति टेंट प्रति रात।",
     "Araku Valley", 1800, ["Check-in 14:00"], 15),

    ("attraction", "Charminar Guided Walk", "चारमीनार गाइडेड वॉक",
     "Guided heritage walk through the Charminar area and old bazaars.",
     "चारमीनार क्षेत्र और पुराने बाज़ारों में गाइड के साथ विरासत भ्रमण।",
     "Hyderabad", 300, ["Morning 09:00", "Evening 17:00"], 30),

    ("attraction", "Golconda Fort Light and Sound Show", "गोलकोंडा किला लाइट एंड साउंड शो",
     "Evening show telling the history of Golconda Fort.",
     "गोलकोंडा किले का इतिहास बताने वाला शाम का शो।",
     "Hyderabad", 200, ["Evening 19:00"], 100),

    ("attraction", "Borra Caves Entry and Guide", "बोर्रा गुफाएँ प्रवेश और गाइड",
     "Entry ticket and guide for the limestone caves near Araku.",
     "अराकू के पास चूना पत्थर की गुफाओं के लिए प्रवेश टिकट और गाइड।",
     "Araku Valley", 150, ["Morning 10:00", "Afternoon 14:00"], 80),

    ("attraction", "Ramoji Film City Day Pass", "रामोजी फिल्म सिटी डे पास",
     "Full-day pass for the film city tour and shows.",
     "फिल्म सिटी टूर और शो के लिए पूरे दिन का पास।",
     "Hyderabad", 1800, ["Day 09:00"], 150),
]

DAYS_AHEAD = 14

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@yatraease.com").strip().lower()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "")

if len(ADMIN_PASSWORD) < 12 or ADMIN_PASSWORD.startswith("CHOOSE_"):
    raise SystemExit("Set your own ADMIN_PASSWORD in .env (at least 12 characters).")
if DEMO_PASSWORD and (len(DEMO_PASSWORD) < 8 or DEMO_PASSWORD.startswith("CHOOSE_")):
    raise SystemExit("Set your own DEMO_PASSWORD in .env (at least 8 characters).")
if os.environ.get("SECRET_KEY", "").startswith("PASTE_"):
    raise SystemExit("Replace the SECRET_KEY placeholder in .env with a generated key.")

with app.app_context():
    db.drop_all()
    db.create_all()

    admin = User(name="Admin", email=ADMIN_EMAIL, role="admin")
    admin.set_password(ADMIN_PASSWORD)
    db.session.add(admin)

    if DEMO_PASSWORD:
        visitor = User(name="Test Visitor", email="visitor@example.com", role="visitor")
        visitor.set_password(DEMO_PASSWORD)
        db.session.add(visitor)

    for (stype, name_en, name_hi, desc_en, desc_hi,
         location, price, slots, capacity) in SERVICES:
        service = Service(type=stype, name_en=name_en, name_hi=name_hi,
                          description_en=desc_en, description_hi=desc_hi,
                          location=location, price=price)
        db.session.add(service)
        db.session.flush()

        for day in range(DAYS_AHEAD):
            slot_date = date.today() + timedelta(days=day)
            for slot in slots:
                db.session.add(Availability(service_id=service.service_id,
                                            date=slot_date, time_slot=slot,
                                            total_capacity=capacity))

    db.session.commit()

    print("Users:", User.query.count())
    print("Services:", Service.query.count())
    print("Availability slots:", Availability.query.count())