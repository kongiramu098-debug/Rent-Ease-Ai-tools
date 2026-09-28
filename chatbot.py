"""Prototype assistant: rule-based intent parsing + database search.
Replies are built only from database rows, so prices/availability are never invented.
Swap `parse()` for a Gemini/OpenAI call later; keep `search()` as the source of truth."""
import re
from datetime import date, timedelta

from .models import Product

CATEGORY_WORDS = {
    "Laptops": ["laptop", "notebook", "macbook"], "Smartphones": ["phone", "smartphone", "mobile", "iphone"],
    "Cameras": ["camera", "dslr", "gopro"], "Tablets": ["tablet", "ipad"],
    "Projectors": ["projector"], "Speakers": ["speaker"],
    "Gaming consoles": ["console", "playstation", "xbox", "ps5"],
    "Computer accessories": ["keyboard", "mouse", "monitor", "accessor"],
}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                "a week": 7, "week": 7}


def parse(text):
    t = text.lower()
    category = next((c for c, ws in CATEGORY_WORDS.items() if any(w in t for w in ws)), None)
    days = None
    m = re.search(r"(\d+)\s*day", t)
    if m:
        days = int(m.group(1))
    else:
        m = re.search(r"(" + "|".join(k for k in NUMBER_WORDS if k != "week" and k != "a week") + r")\s*days?", t)
        if m:
            days = NUMBER_WORDS[m.group(1)]
        elif "week" in t:
            days = 7
    budget = None
    m = re.search(r"(?:under|below|less than|within|max|<)\s*(?:₹|rs\.?|inr)?\s*(\d+)", t)
    if m:
        budget = int(m.group(1))
    return {"category": category, "days": days, "budget": budget}


def search(intent):
    qs = Product.objects.filter(shop__approved=True, category=intent["category"])
    if intent["budget"]:
        qs = qs.filter(daily_price__lte=intent["budget"])
    start = date.today()
    end = start + timedelta(days=(intent["days"] or 1) - 1)
    return [p for p in qs.select_related("shop") if p.is_available(start, end)][:5]


def reply(text):
    intent = parse(text)
    if not intent["category"]:
        return {"reply": "What kind of device do you need? For example: laptop, camera, projector.",
                "products": [], "intent": intent}
    found = search(intent)
    if not found:
        return {"reply": "No available products match that. Try a higher budget or a different device.",
                "products": [], "intent": intent}
    days = intent["days"] or 1
    lines = [f"I found {len(found)} available option(s). Totals are rent only; deposit is charged separately."]
    products = [{
        "id": p.pk, "name": p.name, "shop": p.shop.name, "city": p.shop.city,
        "daily_price": str(p.daily_price), "deposit": str(p.security_deposit),
        "total": str(p.daily_price * days), "days": days, "url": f"/products/{p.pk}/",
    } for p in found]
    if not intent["days"]:
        lines.append("Tell me how many days you need and I'll calculate the total.")
    return {"reply": " ".join(lines), "products": products, "intent": intent}
