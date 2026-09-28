# RentEase AI – prototype

Django prototype of an electronic rental platform. **Written without being run** (no Django in the build sandbox), so run the tests first.

## Run
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations rentals
python manage.py migrate
python manage.py seed
python manage.py test
python manage.py runserver
```

Demo logins: `customer1 / demo12345`, `owner1 / demo12345`, `admin / admin12345` (admin site at `/admin/`, approve shops there).

## PostgreSQL
Copy `.env.example` to `.env`, set `DB_NAME` etc., and export the variables (or use your shell/Render env settings). With `DB_NAME` empty it uses SQLite.

## What works in the prototype
Register/login with roles · search and filter · date-based booking with backend price calculation · double-booking check inside `transaction.atomic` + `select_for_update` · tracking timeline · owner status updates (own shops only) · in-app notifications · nearby shops (Leaflet/OpenStreetMap, backend haversine distance) · rule-based chatbot reading from the DB.

## Stubbed / not built yet
Razorpay (mock payment only) · Gemini/OpenAI (chatbot in `rentals/chatbot.py` is rule-based) · Google Maps · Django REST Framework endpoints · image uploads (URL field) · reviews · shop-owner product forms (use `/admin/`) · reminders · Render deploy config.
