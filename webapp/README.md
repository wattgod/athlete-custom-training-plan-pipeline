# Gravel God Web App

Flask-based web interface for the training plan generation pipeline.

## Setup

```bash
cd webapp
pip install -r requirements.txt
```

## Running

```bash
python app.py
```

The app runs on http://localhost:5000 by default.

## Configuration

- `PORT`: Server port (default: 5000)
- `FLASK_DEBUG`: Enable debug mode (default: true)
- `SECRET_KEY`: Session secret key (set in production)

## Features

- **Athlete List**: View all athletes at `/`
- **Athlete Detail**: View profile, classifications, and run pipeline at `/athlete/<id>`
- **Intake Form**: Create new athletes at `/new`
- **API Endpoints**:
  - `GET /api/athletes` - List all athletes
  - `GET /api/athlete/<id>` - Get athlete data
  - `POST /api/athlete/<id>/generate` - Run full pipeline
  - `POST /api/athlete/<id>/step/<step>` - Run single step

## Pipeline Steps

Available steps: `validate`, `derive`, `methodology`, `fueling`, `structure`, `workouts`, `guide`, `dashboard`
