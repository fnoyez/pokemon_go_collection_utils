import enum


class Region(enum.Enum):
    """The regions species are grouped by, in display order."""

    KANTO = "Kanto"
    JOHTO = "Johto"
    HOENN = "Hoenn"
    SINNOH = "Sinnoh"
    UNOVA = "Unova"
    KALOS = "Kalos"
    ALOLA = "Alola"
    GALAR = "Galar"
    HISUI = "Hisui"
    PALDEA = "Paldea"


# The last National Pokédex number each region introduced, each region starting
# right after the previous one. Meltan and Melmetal belong to the seventh
# generation, hence to Alola; Hisui's species follow Galar's within the eighth.
REGION_LAST_DEX_NUMBERS = {
    Region.KANTO: 151,
    Region.JOHTO: 251,
    Region.HOENN: 386,
    Region.SINNOH: 493,
    Region.UNOVA: 649,
    Region.KALOS: 721,
    Region.ALOLA: 809,
    Region.GALAR: 898,
    Region.HISUI: 905,
    Region.PALDEA: 1025,
}

# The token a form identifier carries when the form is regional, and its region.
REGIONAL_FORM_TOKEN_REGIONS = {
    "ALOLA": Region.ALOLA,
    "GALARIAN": Region.GALAR,
    "HISUIAN": Region.HISUI,
    "PALDEA": Region.PALDEA,
}


def find_region(dex_number):
    """Return the region that introduced the species with this number.

    Reads `REGION_LAST_DEX_NUMBERS` directly: the ranges are the single
    declaration of which region introduced which species, not a setting.
    """
    for region, last_dex_number in REGION_LAST_DEX_NUMBERS.items():
        if dex_number <= last_dex_number:
            return region
    raise ValueError(
        f"No region declared for National Pokédex number {dex_number}: "
        "extend REGION_LAST_DEX_NUMBERS"
    )


def find_regional_form_region(form_suffix_tokens):
    """Return the region of a form from its suffix tokens, or None for a non-regional form.

    Reads `REGIONAL_FORM_TOKEN_REGIONS` directly, for the same reason
    `find_region` reads its ranges.
    """
    for token in form_suffix_tokens:
        if token in REGIONAL_FORM_TOKEN_REGIONS:
            return REGIONAL_FORM_TOKEN_REGIONS[token]
    return None
