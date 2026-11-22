"""Demo scenarios for the leader page and the automated tests (no internet or API key needed)."""

# Demo scenarios: work with no internet and no API key (the 3 required test cases).
# "features" are the upstream-rain numbers the surge model would see.
SCENARIOS = {
    "Sunny here, heavy rain upstream": {
        "rain": 52.0, "age": 1.0,
        "features": {"rain_1d": 18, "rain_3d": 46, "rain_7d": 78, "rain_14d": 104,
                     "max_point_3d": 52, "month": 4, "long_rains": 1, "short_rains": 0},
        "messages": "Habari za asubuhi wote\n"
                    "Maji imeanza kujaa kwa drift, inakuja na nguvu\n"
                    "Watu wanavuka na boda saa hii",
    },
    "Little rain, but villagers see rising water": {
        "rain": 6.0, "age": 1.0,
        "features": {"rain_1d": 1, "rain_3d": 4, "rain_7d": 9, "rain_14d": 15,
                     "max_point_3d": 6, "month": 8, "long_rains": 0, "short_rains": 0},
        "messages": "Maji imejaa kwa drift ya chini\n"
                    "Drift imeharibika upande wa shule",
    },
    "Kikamba reports, little rain upstream (beta)": {
        "rain": 6.0, "age": 1.0,
        "features": {"rain_1d": 1, "rain_3d": 4, "rain_7d": 9, "rain_14d": 15,
                     "max_point_3d": 6, "month": 4, "long_rains": 1, "short_rains": 0},
        "messages": "Usi wausia kiwu, ndukilika\n"
                    "Andu nimaiinga usi yu",
    },
    "Weather service down": {
        "rain": -1.0, "age": 0.0, "features": None,
        "messages": "Mambo vipi, kuna mvua huko juu?",
    },
}
