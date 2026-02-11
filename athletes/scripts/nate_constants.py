"""
Workout Generator Constants
===========================

Centralized configuration for all magic numbers, power targets, and durations
used throughout the Nate workout generator.

All power values are expressed as fractions of FTP (1.0 = 100% FTP).
All durations are in seconds unless otherwise noted.
"""

from typing import Dict, Final

# =============================================================================
# POWER ZONES (as fractions of FTP)
# =============================================================================

class PowerZones:
    """Power zone definitions as FTP fractions."""

    # Recovery / Zone 1
    RECOVERY_LOW: Final[float] = 0.45
    RECOVERY_MID: Final[float] = 0.50
    RECOVERY_HIGH: Final[float] = 0.55

    # Endurance / Zone 2
    ENDURANCE_LOW: Final[float] = 0.56
    ENDURANCE_MID: Final[float] = 0.65
    ENDURANCE_HIGH: Final[float] = 0.75

    # Tempo / Zone 3
    TEMPO_LOW: Final[float] = 0.76
    TEMPO_HIGH: Final[float] = 0.87

    # G-Spot / Sub-threshold (NOT Sweet Spot)
    G_SPOT_LOW: Final[float] = 0.87
    G_SPOT_MID: Final[float] = 0.90
    G_SPOT_HIGH: Final[float] = 0.92

    # Threshold / Zone 4
    THRESHOLD_LOW: Final[float] = 0.93
    THRESHOLD_MID: Final[float] = 0.98
    THRESHOLD_HIGH: Final[float] = 1.00
    FTP: Final[float] = 1.00

    # VO2max / Zone 5
    VO2MAX_LOW: Final[float] = 1.06
    VO2MAX_MID: Final[float] = 1.15
    VO2MAX_HIGH: Final[float] = 1.20

    # Anaerobic / Zone 6
    ANAEROBIC_LOW: Final[float] = 1.21
    ANAEROBIC_MID: Final[float] = 1.30
    ANAEROBIC_HIGH: Final[float] = 1.50

    # Neuromuscular / Sprint
    SPRINT_LOW: Final[float] = 1.50
    SPRINT_MID: Final[float] = 2.00
    SPRINT_HIGH: Final[float] = 2.50


# =============================================================================
# CRITICAL POWER CONVERSION
# =============================================================================

class CriticalPower:
    """
    Critical Power (CP) to FTP conversion factors.

    CP is typically 95-98% of FTP depending on duration and athlete.
    When archetypes specify "% of CP", we convert to FTP for the ZWO file.
    """

    # CP as fraction of FTP (conservative estimate)
    CP_TO_FTP_RATIO: Final[float] = 0.96

    # Common CP-based targets converted to FTP
    # 110% CP ≈ 106% FTP
    ABOVE_CP_110: Final[float] = 1.06
    # 105% CP ≈ 101% FTP
    ABOVE_CP_105: Final[float] = 1.01
    # 115% CP ≈ 110% FTP
    ABOVE_CP_115: Final[float] = 1.10
    # 120% CP ≈ 115% FTP
    ABOVE_CP_120: Final[float] = 1.15

    @staticmethod
    def cp_percent_to_ftp(cp_percent: float) -> float:
        """
        Convert a CP percentage to FTP fraction.

        Args:
            cp_percent: Percentage of CP (e.g., 110 for 110% CP)

        Returns:
            FTP fraction (e.g., 1.06 for 106% FTP)
        """
        return (cp_percent / 100) * CriticalPower.CP_TO_FTP_RATIO


# =============================================================================
# WORKOUT DURATIONS (seconds)
# =============================================================================

class Durations:
    """Standard workout segment durations in seconds."""

    # Warmup durations
    WARMUP_SHORT: Final[int] = 300      # 5 min
    WARMUP_STANDARD: Final[int] = 600   # 10 min
    WARMUP_EXTENDED: Final[int] = 900   # 15 min
    WARMUP_LONG: Final[int] = 1200      # 20 min

    # Cooldown durations
    COOLDOWN_SHORT: Final[int] = 300    # 5 min
    COOLDOWN_STANDARD: Final[int] = 600 # 10 min
    COOLDOWN_LONG: Final[int] = 900     # 15 min

    # Interval durations
    INTERVAL_30S: Final[int] = 30
    INTERVAL_1MIN: Final[int] = 60
    INTERVAL_90S: Final[int] = 90
    INTERVAL_2MIN: Final[int] = 120
    INTERVAL_3MIN: Final[int] = 180
    INTERVAL_4MIN: Final[int] = 240
    INTERVAL_5MIN: Final[int] = 300
    INTERVAL_8MIN: Final[int] = 480     # Norwegian standard
    INTERVAL_10MIN: Final[int] = 600
    INTERVAL_20MIN: Final[int] = 1200

    # Recovery durations between intervals
    RECOVERY_SHORT: Final[int] = 60     # 1 min
    RECOVERY_STANDARD: Final[int] = 120 # 2 min
    RECOVERY_MEDIUM: Final[int] = 180   # 3 min
    RECOVERY_LONG: Final[int] = 240     # 4 min
    RECOVERY_EXTENDED: Final[int] = 300 # 5 min

    # Endurance/base ride durations
    ENDURANCE_SHORT: Final[int] = 2700      # 45 min
    ENDURANCE_STANDARD: Final[int] = 3600   # 60 min
    ENDURANCE_LONG: Final[int] = 5400       # 90 min
    ENDURANCE_EXTENDED: Final[int] = 7200   # 2 hours
    HVLI_SHORT: Final[int] = 10800          # 3 hours
    HVLI_LONG: Final[int] = 14400           # 4 hours


# =============================================================================
# DEFAULT CADENCE VALUES
# =============================================================================

class Cadence:
    """Standard cadence prescriptions in RPM."""

    LOW: Final[int] = 70           # Strength/climbing
    MODERATE_LOW: Final[int] = 80  # Steady climbing
    MODERATE: Final[int] = 85      # General riding
    NORWEGIAN: Final[int] = 88     # Norwegian 4x8 threshold
    STANDARD: Final[int] = 90      # Default cadence
    HIGH: Final[int] = 95          # VO2max work
    VERY_HIGH: Final[int] = 100    # High-cadence drills
    SPRINT: Final[int] = 110       # Sprint efforts


# =============================================================================
# WORKOUT LEVEL BOUNDARIES
# =============================================================================

class Levels:
    """Workout progression level definitions."""

    MIN_LEVEL: Final[int] = 1
    MAX_LEVEL: Final[int] = 6
    DEFAULT_LEVEL: Final[int] = 3
    TAPER_LEVEL: Final[int] = 4

    # Progression thresholds (as fraction of build phase)
    LEVEL_1_THRESHOLD: Final[float] = 0.17
    LEVEL_2_THRESHOLD: Final[float] = 0.33
    LEVEL_3_THRESHOLD: Final[float] = 0.50
    LEVEL_4_THRESHOLD: Final[float] = 0.67
    LEVEL_5_THRESHOLD: Final[float] = 0.83
    # Above 0.83 = Level 6


# =============================================================================
# WORKOUT VALIDATION LIMITS
# =============================================================================

class ValidationLimits:
    """Sanity check limits for generated workouts."""

    # Duration limits (seconds)
    MIN_WORKOUT_DURATION: Final[int] = 900        # 15 min minimum
    MAX_WORKOUT_DURATION: Final[int] = 21600      # 6 hours maximum
    MAX_INTERVAL_DURATION: Final[int] = 3600      # 1 hour max single interval

    # Power limits (FTP fractions)
    MIN_POWER: Final[float] = 0.30                # 30% FTP minimum
    MAX_POWER: Final[float] = 3.00                # 300% FTP maximum (sprint)

    # Repeat limits
    MIN_REPEATS: Final[int] = 1
    MAX_REPEATS: Final[int] = 30                  # Reasonable upper limit

    # XML content limits
    MAX_DESCRIPTION_LENGTH: Final[int] = 5000     # Characters
    MAX_NAME_LENGTH: Final[int] = 100             # Characters


# =============================================================================
# ZWO XML DEFAULTS
# =============================================================================

class ZWODefaults:
    """Default values for ZWO file generation."""

    AUTHOR: Final[str] = "Gravel God Training"
    SPORT_TYPE: Final[str] = "bike"
    XML_VERSION: Final[str] = "1.0"
    XML_ENCODING: Final[str] = "UTF-8"

    # Warmup defaults
    WARMUP_POWER_LOW: Final[float] = PowerZones.RECOVERY_MID
    WARMUP_POWER_HIGH: Final[float] = PowerZones.ENDURANCE_HIGH

    # Cooldown defaults
    COOLDOWN_POWER_LOW: Final[float] = PowerZones.ENDURANCE_HIGH
    COOLDOWN_POWER_HIGH: Final[float] = PowerZones.RECOVERY_MID

    # Recovery interval default
    RECOVERY_POWER: Final[float] = PowerZones.RECOVERY_HIGH


# =============================================================================
# METHODOLOGY DEFAULTS
# =============================================================================

class MethodologyDefaults:
    """Default values for training methodologies."""

    DEFAULT_METHODOLOGY: Final[str] = "POLARIZED"
    DEFAULT_TAPER_WEEKS: Final[int] = 2
    DEFAULT_QUALITY_SESSIONS: Final[int] = 2

    # Polarized ratio
    POLARIZED_EASY_RATIO: Final[float] = 0.80
    POLARIZED_HARD_RATIO: Final[float] = 0.20
