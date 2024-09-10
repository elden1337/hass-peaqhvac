import pytest
from ..service.hvac.offset.peakfinder import identify_peaks

P240910 = [0.07,0.07,0.06,0.06,0.07,0.07,0.08,0.11,0.11,0.11,0.11,0.1,0.08,0.08,0.08,0.08,0.08,0.12,0.12,0.12,0.11,0.1,0.08,0.08]
P240911 = [0.08,0.08,0.08,0.08,0.09,0.11,0.13,0.21,0.6,0.6,0.6,0.59,0.4,0.37,0.32,0.15,0.22,0.35,0.3,0.21,0.14,0.12,0.12,0.11]

def test_no_peaks_found():
    peaks = identify_peaks(P240910)
    assert peaks == []

def test_single_peak():
    peaks = identify_peaks(P240911)
    assert peaks == [17]




