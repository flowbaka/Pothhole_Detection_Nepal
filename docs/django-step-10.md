# Django lesson 10: a project homepage

Open `http://127.0.0.1:8003/` while the Django server is running. The root route now shows a responsive homepage instead of raw JSON. It introduces the capture, review and inform plan, and clearly separates working private APIs from detection and public alerts that are still in development. The road graphic is an illustration, not a map of real hazards.

## How the pieces connect

1. `backend/urls.py` maps `/` to `home()` and `/api/status/` to `api_status()`.
2. `home()` in `backend/views.py` calls `render(request, "backend/home.html")`. `render` loads the HTML template and returns an HTTP response.
3. `TEMPLATES` in `backend/settings.py` tells Django where to find the template. `django.contrib.staticfiles`, `STATIC_URL` and `STATICFILES_DIRS` let the development server serve the stylesheet.
4. `{% load static %}` and `{% static 'backend/home.css' %}` in the template generate the stylesheet URL. The CSS controls spacing, type, colors and the phone layout. No JavaScript or frontend build step is needed for this informational page.
5. `api_status()` preserves the original JSON response at `/api/status/`. The `/health/` and `/health/database/` endpoints keep their existing purposes.

The design uses warm paper, dark green and restrained rust, with a hand-coded SVG road illustration. Its layout changes at narrow widths. Keyboard users can skip the navigation and see a focus indicator. This is a visual milestone; it does not connect the browser recorder to the Django upload API.

## Check it yourself

```powershell
.\.pothholevenv\Scripts\python.exe manage.py check
.\.pothholevenv\Scripts\python.exe manage.py test backend captures --settings=backend.test_settings
.\.pothholevenv\Scripts\python.exe manage.py runserver 127.0.0.1:8003
```

Open `/` on your laptop and narrow the browser window to phone width. Click the navigation and the two hero links. Open `/api/status/` separately to see `{"message":"Django backend is running"}`. These desktop and simulated-viewport checks do not establish that the page was tested on a physical phone.
