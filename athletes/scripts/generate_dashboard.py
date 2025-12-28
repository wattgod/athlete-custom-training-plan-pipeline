#!/usr/bin/env python3
"""
Generate Neo-Brutalist Athlete Dashboard

Creates a coach-first dashboard prioritizing decision-critical information:
1. Race countdown & goal (urgency)
2. Risk factors (red flags)
3. Capacity check (can they handle the plan?)
4. Current status (are they training?)
5. Constraints (what limits them?)
6. Details (equipment, preferences, etc.)
"""

import yaml
import json
import sys
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional


def calculate_days_until(date_str: Optional[str]) -> Optional[int]:
    """Calculate days until a date."""
    if not date_str:
        return None
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()
        return (target - today).days
    except:
        return None


def calculate_current_week(race_date: Optional[str], plan_weeks: int) -> Optional[int]:
    """Calculate current week in plan."""
    days_until = calculate_days_until(race_date)
    if days_until is None or plan_weeks == 0:
        return None
    weeks_until = days_until // 7
    current_week = plan_weeks - weeks_until
    return max(1, min(current_week, plan_weeks))


def format_date(date_str: Optional[str]) -> str:
    """Format date string for display."""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except:
        return date_str


def format_value(value, default="—") -> str:
    """Format a value for display."""
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, list):
        if not value:
            return default
        return ", ".join(str(v).replace("_", " ").title() for v in value)
    return str(value)


def get_risk_level(injuries: List, health: Dict, limitations: Dict, schedule: Dict, lifestyle: Dict, nutrition: Dict) -> str:
    """Determine risk level for athlete."""
    if injuries and any(i.get('severity') in ['moderate', 'significant'] for i in injuries):
        return "HIGH"
    if injuries:
        return "MODERATE"
    if health.get('stress_level') in ['high', 'very_high']:
        return "MODERATE"
    if health.get('sleep_quality') == 'poor':
        return "MODERATE"
    if limitations and any(v in ['limited', 'significantly_limited', 'painful'] for v in limitations.values() if isinstance(v, str)):
        return "MODERATE"
    if schedule.get('travel_frequency') == 'frequent':
        return "MODERATE"
    if lifestyle.get('alcohol_drinks_per_week', 0) > 10:
        return "MODERATE"
    if nutrition.get('fuels_during_rides') == 'rarely':
        return "MODERATE"
    return "LOW"


def generate_dashboard(athlete_id: str) -> Path:
    """
    Generate coach-first Neo-Brutalist dashboard for athlete.
    """
    # Load data
    profile_path = Path(f"athletes/{athlete_id}/profile.yaml")
    derived_path = Path(f"athletes/{athlete_id}/derived.yaml")
    weekly_structure_path = Path(f"athletes/{athlete_id}/weekly_structure.yaml")
    
    with open(profile_path, 'r') as f:
        profile = yaml.safe_load(f)
    
    derived = {}
    if derived_path.exists():
        with open(derived_path, 'r') as f:
            derived = yaml.safe_load(f)
    
    weekly_structure = {}
    if weekly_structure_path.exists():
        with open(weekly_structure_path, 'r') as f:
            weekly_structure = yaml.safe_load(f)
    
    plan_config_path = Path(f"athletes/{athlete_id}/plans/current/plan_config.yaml")
    plan_config = {}
    if plan_config_path.exists():
        with open(plan_config_path, 'r') as f:
            plan_config = yaml.safe_load(f)
    
    name = profile.get('name', athlete_id)
    email = profile.get('email', '')
    target_race = profile.get("target_race", {})
    fitness = profile.get("fitness_markers", {})
    training_history = profile.get("training_history", {})
    recent_training = profile.get("recent_training", {})
    weekly_availability = profile.get("weekly_availability", {})
    preferred_days = profile.get("preferred_days", {})
    health = profile.get("health_factors", {})
    injuries = profile.get("injury_history", {})
    equipment = profile.get("strength_equipment", [])
    cycling_equipment = profile.get("cycling_equipment", {})
    limitations = profile.get("movement_limitations", {})
    schedule_constraints = profile.get("schedule_constraints", {})
    training_env = profile.get("training_environment", {})
    lifestyle = profile.get("lifestyle", {})
    nutrition = profile.get("nutrition", {})
    workout_prefs = profile.get("workout_preferences", {})
    exercise_exclusions = derived.get("exercise_exclusions", [])
    equipment_tier = derived.get("equipment_tier", "")
    
    # Calculate critical metrics
    race_date = target_race.get('date')
    days_until = calculate_days_until(race_date)
    plan_weeks = derived.get('plan_weeks', 0)
    current_week = calculate_current_week(race_date, plan_weeks)
    
    # Risk assessment - enhanced to include all factors
    current_injuries = injuries.get('current_injuries', [])
    past_injuries = injuries.get('past_injuries', [])
    risk_level = get_risk_level(current_injuries, health, limitations, schedule_constraints, lifestyle, nutrition)
    
    # Capacity check
    hours_available = weekly_availability.get('total_hours_available', 0)
    hours_current = training_history.get('current_weekly_hours', 0)
    hours_peak = training_history.get('highest_weekly_hours', 0)
    
    # Generate HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - Coaching Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #ffffff;
            --fg: #000000;
            --border: #000000;
            --muted: #666666;
            --soft: #f5f5f5;
            --warning: #ff0000;
            --success: #00ff00;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background: var(--bg);
            color: var(--fg);
            font-family: "Sometype Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 14px;
            line-height: 1.6;
            padding: 24px;
            max-width: 1600px;
            margin: 0 auto;
        }}

        /* HEADER */
        .header {{
            border: 3px solid var(--border);
            padding: 24px;
            margin-bottom: 32px;
            background: var(--soft);
        }}

        .header h1 {{
            font-size: 32px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            margin-bottom: 8px;
        }}

        .header-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            margin-top: 16px;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}

        .header-meta span {{
            border: 2px solid var(--border);
            padding: 6px 12px;
            background: var(--bg);
        }}

        /* PRIORITY GRID - Top section for critical info */
        .priority-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }}

        /* RACE COUNTDOWN - Most urgent */
        .race-countdown {{
            border: 3px solid var(--border);
            padding: 24px;
            background: var(--soft);
        }}

        .countdown-number {{
            font-size: 72px;
            font-weight: 700;
            line-height: 1;
            margin: 16px 0;
        }}

        .countdown-label {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--muted);
        }}

        /* RISK FACTORS - Red flags */
        .risk-factors {{
            border: 3px solid var(--border);
            padding: 24px;
            background: var(--soft);
        }}

        .risk-high {{
            border-color: var(--warning);
            background: #fff5f5;
        }}

        .risk-moderate {{
            border-color: #ff8800;
            background: #fff8f0;
        }}

        .risk-low {{
            border-color: var(--success);
            background: #f0fff0;
        }}

        .risk-level {{
            font-size: 24px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 16px;
        }}

        /* CAPACITY CHECK */
        .capacity-check {{
            border: 3px solid var(--border);
            padding: 24px;
            margin-bottom: 24px;
        }}

        .capacity-bar {{
            width: 100%;
            height: 40px;
            border: 2px solid var(--border);
            background: var(--soft);
            margin: 8px 0;
            position: relative;
            overflow: hidden;
        }}

        .capacity-fill {{
            height: 100%;
            background: var(--fg);
            transition: width 0.3s;
        }}

        /* GRID LAYOUT */
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }}

        /* CARD STYLES */
        .card {{
            border: 3px solid var(--border);
            padding: 24px;
            background: var(--bg);
        }}

        .card-header {{
            font-size: 18px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--border);
        }}

        .card-content {{
            font-size: 14px;
        }}

        /* KEY-VALUE PAIRS */
        .kv-row {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
        }}

        .kv-row:last-child {{
            border-bottom: none;
        }}

        .kv-key {{
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--muted);
        }}

        .kv-value {{
            font-weight: 500;
            text-align: right;
        }}

        /* FULL WIDTH CARDS */
        .card-full {{
            grid-column: 1 / -1;
        }}

        /* WEEKLY SCHEDULE */
        .schedule-day {{
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 16px;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }}

        .schedule-day:last-child {{
            border-bottom: none;
        }}

        .day-name {{
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}

        .day-content {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .workout-type {{
            font-weight: 600;
        }}

        .workout-notes {{
            font-size: 12px;
            color: var(--muted);
        }}

        /* BADGES */
        .badge {{
            display: inline-block;
            border: 2px solid var(--border);
            padding: 4px 10px;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 600;
            margin: 2px;
        }}

        .badge-key {{
            background: var(--fg);
            color: var(--bg);
        }}

        .badge-warning {{
            background: var(--warning);
            color: var(--bg);
            border-color: var(--warning);
        }}

        /* STATUS INDICATORS */
        .status-good {{
            color: #008800;
        }}

        .status-warning {{
            color: #ff8800;
        }}

        .status-danger {{
            color: var(--warning);
        }}

        @media (max-width: 768px) {{
            .priority-grid {{
                grid-template-columns: 1fr;
            }}
            
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
            
            body {{
                padding: 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{name.upper()}</h1>
        <div class="header-meta">
            <span>ID: {athlete_id}</span>
            <span>EMAIL: {email}</span>
            <span>TIER: {derived.get('tier', 'N/A').upper()}</span>
        </div>
    </div>

    <!-- PRIORITY SECTION: Race Countdown + Risk Factors -->
    <div class="priority-grid">
        <!-- RACE COUNTDOWN -->
        <div class="race-countdown">
            <div class="card-header">RACE COUNTDOWN</div>
            <div class="countdown-number">{days_until if days_until is not None else "—"}</div>
            <div class="countdown-label">DAYS UNTIL RACE</div>
            <div style="margin-top: 24px;">
                <div class="kv-row">
                    <span class="kv-key">Race</span>
                    <span class="kv-value">{format_value(target_race.get('name'))}</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Date</span>
                    <span class="kv-value">{format_date(race_date)}</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Distance</span>
                    <span class="kv-value">{format_value(target_race.get('distance_miles'))} MILES</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Goal</span>
                    <span class="kv-value">{format_value(target_race.get('goal_type')).upper()}</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Plan Week</span>
                    <span class="kv-value">{current_week if current_week else "—"} / {plan_weeks}</span>
                </div>
            </div>
        </div>

        <!-- RISK FACTORS -->
        <div class="risk-factors risk-{risk_level.lower()}">
            <div class="card-header">RISK FACTORS</div>
            <div class="risk-level">RISK: {risk_level}</div>
            
            {format_risk_factors(current_injuries, health, limitations, past_injuries, exercise_exclusions, schedule_constraints, training_env, lifestyle, nutrition, equipment_tier, workout_prefs, profile)}
        </div>
    </div>

    <!-- CAPACITY CHECK -->
    <div class="capacity-check">
        <div class="card-header">CAPACITY CHECK</div>
        <div style="margin-top: 16px;">
            <div class="kv-row">
                <span class="kv-key">Hours Available</span>
                <span class="kv-value">{hours_available} H/WEEK</span>
            </div>
            <div class="capacity-bar">
                <div class="capacity-fill" style="width: {min(100, (hours_available / max(20, 1)) * 100)}%;"></div>
            </div>
            <div class="kv-row">
                <span class="kv-key">Currently Doing</span>
                <span class="kv-value">{hours_current} H/WEEK</span>
            </div>
            <div class="kv-row">
                <span class="kv-key">Peak Ever Sustained</span>
                <span class="kv-value">{hours_peak} H/WEEK</span>
            </div>
            <div class="kv-row">
                <span class="kv-key">Training Consistency</span>
                <span class="kv-value {get_consistency_class(recent_training.get('last_12_weeks'))}">{format_value(recent_training.get('last_12_weeks')).upper()}</span>
            </div>
            <div class="kv-row">
                <span class="kv-key">Days Since Last Ride</span>
                <span class="kv-value {get_days_class(recent_training.get('days_since_last_ride'))}">{format_value(recent_training.get('days_since_last_ride'))}</span>
            </div>
        </div>
    </div>

    <div class="dashboard-grid">
        <!-- CURRENT FITNESS -->
        <div class="card">
            <div class="card-header">CURRENT FITNESS</div>
            <div class="card-content">
                <div class="kv-row">
                    <span class="kv-key">FTP</span>
                    <span class="kv-value">{format_value(fitness.get('ftp_watts'))} W</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">W/KG</span>
                    <span class="kv-value">{format_value(fitness.get('w_kg'))}</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">FTP Date</span>
                    <span class="kv-value">{format_date(fitness.get('ftp_date'))}</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Weight</span>
                    <span class="kv-value">{format_value(fitness.get('weight_kg'))} KG</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Resting HR</span>
                    <span class="kv-value">{format_value(fitness.get('resting_hr'))} BPM</span>
                </div>
            </div>
        </div>

        <!-- TRAINING EXPERIENCE -->
        <div class="card">
            <div class="card-header">TRAINING EXPERIENCE</div>
            <div class="card-content">
                <div class="kv-row">
                    <span class="kv-key">Years Cycling</span>
                    <span class="kv-value">{format_value(training_history.get('years_cycling'))}</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Years Structured</span>
                    <span class="kv-value">{format_value(training_history.get('years_structured'))}</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Strength Background</span>
                    <span class="kv-value">{format_value(training_history.get('strength_background')).upper()}</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Current Phase</span>
                    <span class="kv-value">{format_value(recent_training.get('current_phase')).upper()}</span>
                </div>
                <div class="kv-row">
                    <span class="kv-key">Coming Off Injury</span>
                    <span class="kv-value {get_yes_no_class(recent_training.get('coming_off_injury'))}">{format_value(recent_training.get('coming_off_injury'))}</span>
                </div>
            </div>
        </div>

        <!-- KEY DAYS -->
        <div class="card">
            <div class="card-header">KEY TRAINING DAYS</div>
            <div class="card-content">
                {format_day_list(derived.get('key_day_candidates', []))}
                <div style="margin-top: 16px; font-size: 12px; color: var(--muted);">
                    Days marked for high-intensity work
                </div>
            </div>
        </div>

        <!-- EQUIPMENT -->
        <div class="card">
            <div class="card-header">EQUIPMENT</div>
            <div class="card-content">
                <div style="margin-bottom: 16px;">
                    <div class="kv-key" style="margin-bottom: 8px;">STRENGTH</div>
                    {format_equipment_list(equipment)}
                </div>
                <div>
                    <div class="kv-key" style="margin-bottom: 8px;">CYCLING</div>
                    <div class="kv-row">
                        <span class="kv-key">Smart Trainer</span>
                        <span class="kv-value">{format_value(cycling_equipment.get('smart_trainer'))}</span>
                    </div>
                    <div class="kv-row">
                        <span class="kv-key">Power Meter</span>
                        <span class="kv-value">{format_value(cycling_equipment.get('power_meter_bike'))}</span>
                    </div>
                    <div class="kv-row">
                        <span class="kv-key">HR Monitor</span>
                        <span class="kv-value">{format_value(cycling_equipment.get('hr_monitor'))}</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- WEEKLY SCHEDULE -->
        <div class="card card-full">
            <div class="card-header">WEEKLY SCHEDULE</div>
            <div class="card-content">
                {format_weekly_schedule(weekly_structure.get('days', {}))}
            </div>
        </div>
    </div>

    <div style="text-align: center; margin-top: 48px; padding-top: 24px; border-top: 3px solid var(--border); font-size: 12px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted);">
        GENERATED {datetime.now().strftime('%B %d, %Y AT %H:%M').upper()}
    </div>
</body>
</html>'''

    # Write dashboard
    dashboard_path = Path(f"athletes/{athlete_id}/dashboard.html")
    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dashboard_path, 'w') as f:
        f.write(html)
    
    return dashboard_path


def format_risk_factors(current_injuries: List, health: Dict, limitations: Dict, past_injuries: List, 
                       exercise_exclusions: List, schedule: Dict, training_env: Dict, 
                       lifestyle: Dict, nutrition: Dict, equipment_tier: str, workout_prefs: Dict, profile: Dict) -> str:
    """Format comprehensive risk factors section showing all limitations and plan adaptations."""
    factors = []
    
    # CURRENT INJURIES
    if current_injuries:
        for injury in current_injuries:
            area = injury.get('area', 'Unknown')
            severity = injury.get('severity', 'Unknown')
            affects_cycling = injury.get('affects_cycling', False)
            affects_strength = injury.get('affects_strength', False)
            exercises_to_avoid = injury.get('exercises_to_avoid', [])
            notes = injury.get('notes', '')
            
            impact = []
            if affects_cycling:
                impact.append("CYCLING")
            if affects_strength:
                impact.append("STRENGTH")
            
            factors.append(f'''
                <div style="margin: 12px 0; padding: 12px; border: 2px solid var(--border);">
                    <div style="font-weight: 700; text-transform: uppercase;">CURRENT: {area.upper()} ({severity.upper()})</div>
                    <div style="font-size: 12px; margin-top: 4px;">Affects: {', '.join(impact) if impact else 'NONE'}</div>
                    {f'<div style="font-size: 12px; margin-top: 4px;"><strong>Exercises Excluded:</strong> {", ".join(exercises_to_avoid)}</div>' if exercises_to_avoid else ''}
                    {f'<div style="font-size: 12px; margin-top: 4px; color: var(--muted);">{notes}</div>' if notes else ''}
                </div>
            ''')
    else:
        factors.append('<div style="color: var(--muted);">NO CURRENT INJURIES</div>')
    
    # PAST INJURIES NOT RESOLVED
    unresolved = [i for i in past_injuries if not i.get('fully_resolved', True)]
    if unresolved:
        for injury in unresolved:
            area = injury.get('area', 'Unknown')
            year = injury.get('year', '')
            notes = injury.get('notes', '')
            factors.append(f'''
                <div style="margin: 12px 0; padding: 12px; border: 2px solid var(--border); background: var(--soft);">
                    <div style="font-weight: 700; text-transform: uppercase;">PAST: {area.upper()} ({year})</div>
                    <div style="font-size: 11px; margin-top: 4px; color: var(--muted);">NOT FULLY RESOLVED</div>
                    {f'<div style="font-size: 12px; margin-top: 4px; color: var(--muted);">{notes}</div>' if notes else ''}
                </div>
            ''')
    
    # EXERCISE EXCLUSIONS (How plan was adapted)
    if exercise_exclusions:
        factors.append(f'''
            <div style="margin: 16px 0; padding: 12px; border: 2px solid var(--border); background: var(--soft);">
                <div style="font-weight: 700; text-transform: uppercase; margin-bottom: 8px;">PLAN ADAPTATIONS</div>
                <div style="font-size: 12px; margin-bottom: 4px;"><strong>Exercises Excluded:</strong></div>
                <div style="margin-top: 4px;">{", ".join([f'<span class="badge" style="text-decoration: line-through;">{ex.upper()}</span>' for ex in exercise_exclusions])}</div>
            </div>
        ''')
    
    # MOVEMENT LIMITATIONS
    if limitations:
        limited = [k for k, v in limitations.items() if isinstance(v, str) and v in ['limited', 'significantly_limited', 'painful']]
        if limited:
            factors.append(f'<div style="margin-top: 8px;"><span class="badge">MOVEMENT LIMITATIONS: {", ".join([l.replace("_", " ").upper() for l in limited[:3]])}</span></div>')
        if limitations.get('notes'):
            factors.append(f'<div style="font-size: 11px; margin-top: 4px; color: var(--muted);">{limitations.get("notes")}</div>')
    
    # HEALTH CONCERNS
    if health.get('stress_level') in ['high', 'very_high']:
        factors.append(f'<div style="margin-top: 8px;"><span class="badge badge-warning">HIGH STRESS</span></div>')
    
    if health.get('sleep_quality') == 'poor':
        factors.append(f'<div style="margin-top: 8px;"><span class="badge badge-warning">POOR SLEEP ({health.get("sleep_hours_avg", "?")}H/NIGHT)</span></div>')
    elif health.get('sleep_hours_avg', 0) < 7:
        factors.append(f'<div style="margin-top: 8px;"><span class="badge">LOW SLEEP ({health.get("sleep_hours_avg")}H/NIGHT)</span></div>')
    
    if health.get('recovery_capacity') == 'slow':
        factors.append(f'<div style="margin-top: 8px;"><span class="badge">SLOW RECOVERY</span></div>')
    
    # SCHEDULE CONSTRAINTS
    if schedule.get('travel_frequency') in ['occasional', 'frequent']:
        factors.append(f'<div style="margin-top: 8px;"><span class="badge">TRAVEL: {schedule.get("travel_frequency").upper()}</span></div>')
    
    if schedule.get('family_commitments'):
        factors.append(f'<div style="margin-top: 8px; font-size: 11px; color: var(--muted);">FAMILY: {schedule.get("family_commitments")}</div>')
    
    # LIFE FACTORS
    if lifestyle.get('alcohol_drinks_per_week', 0) > 7:
        factors.append(f'<div style="margin-top: 8px;"><span class="badge">HIGH ALCOHOL ({lifestyle.get("alcohol_drinks_per_week")}/WEEK)</span></div>')
    
    if lifestyle.get('caffeine_mg_per_day', 0) > 400:
        factors.append(f'<div style="margin-top: 8px;"><span class="badge">HIGH CAFFEINE ({lifestyle.get("caffeine_mg_per_day")}MG/DAY)</span></div>')
    
    if lifestyle.get('family_support') == 'challenging':
        factors.append(f'<div style="margin-top: 8px;"><span class="badge badge-warning">FAMILY SUPPORT: CHALLENGING</span></div>')
    
    # NUTRITION CONCERNS
    if nutrition.get('fuels_during_rides') == 'rarely':
        factors.append(f'<div style="margin-top: 8px;"><span class="badge badge-warning">INCONSISTENT FUELING</span></div>')
    
    # EQUIPMENT CONSTRAINTS
    if equipment_tier and equipment_tier != 'high':
        factors.append(f'<div style="margin-top: 8px;"><span class="badge">EQUIPMENT TIER: {equipment_tier.upper()}</span></div>')
    
    # TRAINING ENVIRONMENT
    if training_env.get('indoor_riding_tolerance') == 'hate_it':
        factors.append(f'<div style="margin-top: 8px;"><span class="badge">HATES INDOOR RIDING</span></div>')
    elif training_env.get('indoor_riding_tolerance') == 'tolerate_it':
        max_indoor = workout_prefs.get('longest_indoor_tolerable', '?')
        factors.append(f'<div style="margin-top: 8px; font-size: 11px; color: var(--muted);">Tolerates indoor (max {max_indoor} min)</div>')
    
    if training_env.get('outdoor_riding_access') in ['limited', 'poor']:
        factors.append(f'<div style="margin-top: 8px;"><span class="badge">LIMITED OUTDOOR ACCESS</span></div>')
    
    return '\n'.join(factors)


def get_consistency_class(consistency: Optional[str]) -> str:
    """Get CSS class for training consistency."""
    if consistency == 'consistent':
        return 'status-good'
    elif consistency == 'sporadic':
        return 'status-warning'
    elif consistency == 'none':
        return 'status-danger'
    return ''


def get_days_class(days: Optional[int]) -> str:
    """Get CSS class for days since last ride."""
    if days is None:
        return ''
    if days <= 3:
        return 'status-good'
    elif days <= 7:
        return 'status-warning'
    else:
        return 'status-danger'


def get_yes_no_class(value: bool) -> str:
    """Get CSS class for yes/no values."""
    if value:
        return 'status-warning'
    return 'status-good'


def format_equipment_list(equipment: List[str]) -> str:
    """Format equipment list."""
    if not equipment:
        return '<div class="kv-value">BODYWEIGHT ONLY</div>'
    
    items = []
    for item in equipment:
        items.append(f'<span class="badge">{item.replace("_", " ").upper()}</span>')
    return '<div>' + ' '.join(items) + '</div>'


def format_weekly_schedule(days: Dict) -> str:
    """Format weekly schedule."""
    if not days:
        return '<div class="kv-value">NO SCHEDULE AVAILABLE</div>'
    
    day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    schedule_html = []
    
    for day in day_order:
        if day not in days:
            continue
        
        day_data = days[day]
        day_name = day.upper()
        key_badge = '<span class="badge badge-key">KEY</span>' if day_data.get('is_key_day') else ''
        
        am = day_data.get('am') or ''
        pm = day_data.get('pm') or ''
        
        if am and pm:
            workout = f"{am.upper()} (AM) + {pm.upper()} (PM)"
        elif am:
            workout = am.upper()
        elif pm:
            workout = f"{pm.upper()} (PM)"
        else:
            workout = "REST"
        
        notes = day_data.get('notes', '')
        max_duration = day_data.get('max_duration', '')
        
        schedule_html.append(f'''
            <div class="schedule-day">
                <div class="day-name">{day_name} {key_badge}</div>
                <div class="day-content">
                    <div class="workout-type">{workout}</div>
                    {f'<div class="workout-notes">{notes}</div>' if notes else ''}
                    {f'<div class="workout-notes">MAX: {max_duration} MIN</div>' if max_duration else ''}
                </div>
            </div>
        ''')
    
    return '\n'.join(schedule_html)


def format_day_list(days: List[str]) -> str:
    """Format list of days."""
    if not days:
        return '<div class="kv-value">NONE</div>'
    
    badges = [f'<span class="badge badge-key">{day.upper()}</span>' for day in days]
    return '<div>' + ' '.join(badges) + '</div>'


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python generate_dashboard.py <athlete_id>")
        sys.exit(1)
    
    athlete_id = sys.argv[1]
    
    try:
        dashboard_path = generate_dashboard(athlete_id)
        print(f"✅ Dashboard generated: {dashboard_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
