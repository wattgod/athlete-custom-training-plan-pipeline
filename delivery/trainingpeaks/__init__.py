"""Versioned TrainingPeaks manifest adapter (undocumented API isolated here)."""
from .adapter import (TrainingPeaksAdapter, TrainingPeaksAdapterDisabled,
                      TrainingPeaksReadbackMismatch)

__all__ = ['TrainingPeaksAdapter', 'TrainingPeaksAdapterDisabled',
           'TrainingPeaksReadbackMismatch']
