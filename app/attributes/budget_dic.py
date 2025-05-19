# average_prices_data.py

average_prices = {
    "cultural": {
        "Europe": {"price": 22, "currency": "EUR"},  # Louvre museum entry:contentReference[oaicite:0]{index=0}
        "North America": {"price": 10, "currency": "USD"},  # USA average museum admission:contentReference[oaicite:1]{index=1}
        "South America": {"price": 20, "currency": "BRL"},  # e.g. Brazilian museum ticket
        "Asia": {"price": 60, "currency": "CNY"},  # Forbidden City ticket:contentReference[oaicite:2]{index=2}
        "Africa": {"price": 50, "currency": "ZAR"},  # South African museum entry:contentReference[oaicite:3]{index=3}
        "Oceania": {"price": 20, "currency": "AUD"}  # typical attraction entry
    },
    "outdoor": {
        "Europe": {"price": 10, "currency": "EUR"},  # e.g. national park/day tour fee
        "North America": {"price": 35, "currency": "USD"},  # US National Park fee
        "South America": {"price": 50, "currency": "BRL"},  # Iguazu Falls ~BRL 200 (~$40)
        "Asia": {"price": 60, "currency": "CNY"},  # Great Wall admission:contentReference[oaicite:4]{index=4}
        "Africa": {"price": 100, "currency": "ZAR"},  # Kruger Park day fee
        "Oceania": {"price": 20, "currency": "AUD"}  # park/beach entry
    },
    "shopping": {
        "Europe": {"price": 40, "currency": "EUR"},
        "North America": {"price": 50, "currency": "USD"},
        "South America": {"price": 200, "currency": "BRL"},
        "Asia": {"price": 500, "currency": "CNY"},
        "Africa": {"price": 500, "currency": "ZAR"},
        "Oceania": {"price": 80, "currency": "AUD"}
    },
    "food": {
        "Europe": {"price": 10, "currency": "EUR"},  # fast-food combo:contentReference[oaicite:5]{index=5}
        "North America": {"price": 15, "currency": "USD"}, 
        "South America": {"price": 25, "currency": "BRL"},
        "Asia": {"price": 100, "currency": "CNY"},
        "Africa": {"price": 100, "currency": "ZAR"},
        "Oceania": {"price": 15, "currency": "AUD"}
    },
    "entertainment": {
        "Europe": {"price": 12, "currency": "EUR"},
        "North America": {"price": 14, "currency": "USD"},  # movie ticket:contentReference[oaicite:6]{index=6}
        "South America": {"price": 20, "currency": "BRL"},
        "Asia": {"price": 100, "currency": "CNY"},
        "Africa": {"price": 100, "currency": "ZAR"},
        "Oceania": {"price": 20, "currency": "AUD"}
    },
    "transportation": {
        "Europe": {"price": 3, "currency": "EUR"},
        "North America": {"price": 2.9, "currency": "USD"},  # NYC subway fare:contentReference[oaicite:7]{index=7}
        "South America": {"price": 5, "currency": "BRL"},  # São Paulo bus fare:contentReference[oaicite:8]{index=8}
        "Asia": {"price": 3, "currency": "CNY"},
        "Africa": {"price": 8, "currency": "ZAR"},
        "Oceania": {"price": 4, "currency": "AUD"}
    },
    "accommodation": {
        "Europe": {"price": 80, "currency": "EUR"},  # budget hotel:contentReference[oaicite:9]{index=9}
        "North America": {"price": 175, "currency": "USD"},  # average NYC hotel:contentReference[oaicite:10]{index=10}
        "South America": {"price": 200, "currency": "BRL"},
        "Asia": {"price": 500, "currency": "CNY"},
        "Africa": {"price": 800, "currency": "ZAR"},
        "Oceania": {"price": 96, "currency": "AUD"}  # average Sydney hotel:contentReference[oaicite:11]{index=11}
    },
    "wellness": {
        "Europe": {"price": 20, "currency": "EUR"},
        "North America": {"price": 25, "currency": "USD"},
        "South America": {"price": 100, "currency": "BRL"},
        "Asia": {"price": 200, "currency": "CNY"},
        "Africa": {"price": 200, "currency": "ZAR"},
        "Oceania": {"price": 40, "currency": "AUD"}
    },
    "sports": {
        "Europe": {"price": 30, "currency": "EUR"},
        "North America": {"price": 50, "currency": "USD"},
        "South America": {"price": 100, "currency": "BRL"},
        "Asia": {"price": 100, "currency": "CNY"},
        "Africa": {"price": 100, "currency": "ZAR"},
        "Oceania": {"price": 50, "currency": "AUD"}
    },
    "nightlife": {
        "Europe": {"price": 10, "currency": "EUR"},  # cocktail:contentReference[oaicite:12]{index=12}
        "North America": {"price": 12, "currency": "USD"},
        "South America": {"price": 30, "currency": "BRL"},
        "Asia": {"price": 50, "currency": "CNY"},
        "Africa": {"price": 50, "currency": "ZAR"},
        "Oceania": {"price": 18, "currency": "AUD"}
    },
    "landmarks": {
        "Europe": {"price": 20, "currency": "EUR"},
        "North America": {"price": 25, "currency": "USD"},
        "South America": {"price": 100, "currency": "BRL"},
        "Asia": {"price": 60, "currency": "CNY"},
        "Africa": {"price": 200, "currency": "ZAR"},
        "Oceania": {"price": 40, "currency": "AUD"}
    }
}

