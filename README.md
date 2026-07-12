# 💪 Fitness Assistant

An AI-powered fitness coach built with **Streamlit** and **Google Gemini**. It
generates a personalized 7-day workout and nutrition plan from your profile, and
adapts each new plan based on the weekly feedback you give it.

## Features

- **Personalized plans** — tailored to your goal, experience, available days, and equipment.
- **Adaptive coaching** — your last few weeks of feedback are fed into the next plan.
- **Profile dashboard** — goal, training days, weight, and computed BMI at a glance.
- **Local & private** — your profile and feedback are stored on your machine in `data/` (never committed).
- **Download plans** — export any plan as Markdown.

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Gemini API key
#    Create a .env file with:
echo 'GEMINI_API_KEY="your-key-here"' > .env
```

Get a free Gemini API key at <https://aistudio.google.com/apikey>.

## Run

```bash
streamlit run app.py
```

The app opens at <http://localhost:8501>. Fill in your profile in the sidebar,
save it, then generate your first plan.

## Tech

- [Streamlit](https://streamlit.io/) — UI
- [google-genai](https://pypi.org/project/google-genai/) — Gemini API client
- [python-dotenv](https://pypi.org/project/python-dotenv/) — environment config
