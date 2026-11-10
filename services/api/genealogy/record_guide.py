"""Where to look next: which records could exist for a person, who holds them, and cost.

Rules come from checked guidance (each route names its source and when it was checked).
Routes marked unchecked are leads, and say so. This never claims a record exists, only
where one would be if it does (ADR-041).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

CHECKED = "2026-11-10"
TNA_CENSUS = (
    "https://www.nationalarchives.gov.uk/help-with-your-research/research-guides/census-records"
)
TNA_BMD = "https://www.nationalarchives.gov.uk/help-with-your-research/research-guides/birth-marriage-death-england-and-wales"
TNA_1939 = (
    "https://www.nationalarchives.gov.uk/help-with-your-research/research-guides/1939-register"
)
GRO = "https://www.gro.gov.uk/gro/content/certificates/faq.asp"
PROBATE = "https://www.gov.uk/search-will-probate"
NRS = "https://www.nrscotland.gov.uk/learning-and-events/research-guides/statutory-registers-of-births-deaths-and-marriages"
TNA_MOD = "https://www.nationalarchives.gov.uk/about-us/how-we-work/plans-policies-performance-and-projects/our-projects/ministry-of-defence-service-records-project/"
FREEUKGEN = "https://www.freeukgenealogy.org.uk/"

CENSUS_YEARS = [1841, 1851, 1861, 1871, 1881, 1891, 1901, 1911, 1921]
CIVIL_REGISTRATION = 1837  # 1 July 1837, England and Wales
SCOTTISH_REGISTRATION = 1855  # 1 January 1855
PROBATE_FROM = 1858


@dataclass
class Route:
    title: str
    holder: str
    what_it_gives: str
    access: str  # free | paid | visit | ask
    cost: str = ""
    url: str = ""
    source: str = ""
    checked: bool = True
    note: str = ""


@dataclass
class Step:
    event: str
    year: str
    why: str
    routes: list[Route] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "routes": [asdict(r) for r in self.routes]}


def _scotland(place: str) -> bool:
    return "scotland" in place.lower()


def _civil(event: str, year: int, place: str) -> list[Route]:
    """Civil registration of a birth, marriage or death."""
    if _scotland(place):
        if year < SCOTTISH_REGISTRATION:
            return []
        closure = {"birth": 100, "marriage": 75, "death": 50}[event]
        return [
            Route(
                "Statutory register entry (Scotland)",
                "National Records of Scotland, via ScotlandsPeople",
                f"The full register entry for a {event}.",
                "paid",
                f"Online images only once the entry is over {closure} years old; "
                "newer entries as official certificates.",
                NRS,
                "National Records of Scotland",
            )
        ]
    if year < CIVIL_REGISTRATION:
        return []
    routes = [
        Route(
            "FreeBMD index",
            "Free UK Genealogy (volunteers)",
            "The quarter, registration district and reference, from the GRO indexes.",
            "free",
            url="https://www.freebmd.org.uk/",
            source="Free UK Genealogy",
        )
    ]
    if event in ("birth", "death"):
        online = (event == "birth" and year <= date.today().year - 100) or (
            event == "death" and year <= 1957
        )
        routes.append(
            Route(
                "GRO historical index and register image",
                "General Register Office",
                f"The {event} index, then an image or PDF of the register entry itself.",
                "free" if online else "paid",
                "Index free to search; Online View image about £3, PDF about £8 (check "
                "current fees). Needs the GRO index reference. Images aren't certified "
                "copies."
                if online
                else "Outside the online index: order a certificate from the GRO.",
                GRO,
                "General Register Office FAQ",
            )
        )
    else:
        routes.append(
            Route(
                "Marriage certificate",
                "General Register Office or the local register office",
                "A copy of the full register entry.",
                "paid",
                "Order with the index reference from FreeBMD.",
                TNA_BMD,
                "The National Archives",
            )
        )
    return routes


def _church(event: str, year: int, place: str, county_office: str) -> list[Route]:
    """Baptism, marriage or burial in a church register."""
    if _scotland(place):
        return [
            Route(
                "Old parish registers (Scotland)",
                "National Records of Scotland, via ScotlandsPeople",
                f"The church record of the {event}.",
                "paid",
                url="https://www.scotlandspeople.gov.uk/",
                source="ScotlandsPeople",
                checked=False,
            )
        ]
    routes = [
        Route(
            "Parish register",
            county_office,
            f"The {event} entry as the church recorded it.",
            "visit",
            "Many county record offices have licensed their registers to subscription "
            "sites; the originals can be seen at the record office.",
            TNA_BMD,
            "The National Archives",
        ),
        Route(
            "FreeREG transcriptions",
            "Free UK Genealogy (volunteers)",
            "Transcribed baptisms, marriages and burials, where a volunteer has covered the "
            "parish.",
            "free",
            url="https://www.freereg.org.uk/",
            source="Free UK Genealogy",
        ),
    ]
    if not _scotland(place):
        routes.append(
            Route(
                "Nonconformist registers",
                "The National Archives (RG 4 to RG 8)",
                "Chapel and other nonconformist registers, mostly before 1837.",
                "free",
                "Available online through The National Archives' partners.",
                TNA_BMD,
                "The National Archives",
            )
        )
    return routes


def _census(year: int, place: str = "") -> list[Route]:
    if _scotland(place):
        return [
            Route(
                f"{year} census (Scotland)",
                "National Records of Scotland, via ScotlandsPeople",
                "Household members, ages, occupations and birthplaces.",
                "paid",
                url="https://www.scotlandspeople.gov.uk/",
                source="ScotlandsPeople",
                checked=False,
            )
        ]
    if year == 1921:
        return [
            Route(
                "1921 census",
                "The National Archives (online through Findmypast)",
                "Household members, ages, occupations and birthplaces.",
                "paid",
                "Free to view at The National Archives (Kew), Manchester Central Library and "
                "the National Library of Wales.",
                TNA_CENSUS,
                "The National Archives",
            )
        ]
    return [
        Route(
            f"{year} census",
            "The National Archives (online through Ancestry and Findmypast)",
            "Household members, ages, occupations and birthplaces.",
            "free",
            "Free indexes on FamilySearch; free images at Kew and many libraries and record "
            "offices; paid on Ancestry and Findmypast.",
            TNA_CENSUS,
            "The National Archives",
        ),
        Route(
            "FreeCEN transcriptions",
            "Free UK Genealogy (volunteers)",
            "Transcribed census entries, where a volunteer has covered the area.",
            "free",
            url="https://www.freecen.org.uk/",
            source="Free UK Genealogy",
        ),
    ]


def record_office_for(place: str) -> str:
    """The record office for a place we know; otherwise a general pointer."""
    low = place.lower()
    if any(w in low for w in ("berkshire", "newbury", "reading", "hungerford", "thatcham")):
        return "Royal Berkshire Archives (Berkshire Record Office)"
    return "The county record office for the parish"


def where_to_look(
    facts: dict[str, dict[str, Any]],
    county_office: str = "The county record office",
    sex: str = "",
) -> list[Step]:
    """Steps for one person from their facts: {"birth": {"year": 1921, "place": "…"}, …}."""
    steps: list[Step] = []
    birth = facts.get("birth") or facts.get("baptism") or {}
    death = facts.get("death") or facts.get("burial") or {}
    born, died = birth.get("year"), death.get("year")
    place = " ".join(str(f.get("place", "")) for f in facts.values())

    for event in ("birth", "death"):
        f = facts.get(event)
        if f and f.get("year"):
            routes = _civil(event, f["year"], f.get("place", ""))
            if routes:
                steps.append(
                    Step(event, str(f["year"]), f"Civil registration of the {event}.", routes)
                )
    for event, church_event in (("baptism", "baptism"), ("burial", "burial")):
        f = facts.get(event)
        if f and f.get("year"):
            steps.append(
                Step(
                    church_event,
                    str(f["year"]),
                    f"The church record of the {church_event}.",
                    _church(church_event, f["year"], f.get("place", ""), county_office),
                )  # fmt: skip
            )
    if born and not facts.get("baptism"):
        why = "A baptism usually follows a birth within weeks or months."
        if born < CIVIL_REGISTRATION or (_scotland(place) and born < SCOTTISH_REGISTRATION):
            why += " Before civil registration, it is usually the main record of a birth."
        steps.append(
            Step(
                "baptism",
                f"about {born}",
                why,
                _church("baptism", born, birth.get("place", ""), county_office),
            )  # fmt: skip
        )

    if born:
        last = died if died else born + 100
        for y in CENSUS_YEARS:
            if born - 1 <= y <= last and (not died or y <= died):
                steps.append(
                    Step(
                        "census", str(y), f"Alive in {y} on the dates recorded.", _census(y, place)
                    )
                )
        if born <= 1939 and (not died or died >= 1939) and not _scotland(place):
            steps.append(
                Step(
                    "1939 Register",
                    "1939",
                    "Taken on 29 September 1939; there was no 1931 census to use (destroyed in "
                    "1942) and none in 1941.",
                    [
                        Route(
                            "1939 Register",
                            "The National Archives (online through Findmypast and Ancestry)",
                            "Name, address, date of birth and occupation.",
                            "paid",
                            "",
                            TNA_1939,
                            "The National Archives",
                        )
                    ],
                )  # fmt: skip
            )
        # MOD-held records are twentieth-century service: not for people born much earlier.
        if 1870 <= born < 1940:
            steps.append(
                Step(
                    "military service",
                    "if they served",
                    "Service records for people born before 1940 are moving from the Ministry of "
                    "Defence to The National Archives.",
                    [
                        Route(
                            "Ministry of Defence service records",
                            "The National Archives",
                            "Service history, units and postings.",
                            "paid",
                            "Search and copy fees since 2 February 2026; some are on Ancestry "
                            "(people born over 100 years ago).",
                            TNA_MOD,
                            "The National Archives",
                        ),
                        Route(
                            "Commonwealth War Graves Commission",
                            "CWGC",
                            "If they died in either world war: burial or memorial.",
                            "free",
                            url="https://www.cwgc.org/",
                            source="CWGC",
                            checked=False,
                        ),
                    ],
                )  # fmt: skip
            )

    if died and died >= PROBATE_FROM and not _scotland(place):
        steps.append(
            Step(
                "probate",
                f"from {died}",
                "If they left a will or an estate was administered.",
                [
                    Route(
                        "Probate calendar and copies (England and Wales)",
                        "HM Courts and Tribunals Service (Find a will)",
                        "The calendar entry, and copies of the grant and will.",
                        "paid",
                        "Search free; £16 per copy ordered online (checked 10 Nov 2026).",
                        PROBATE,
                        "GOV.UK",
                    )
                ],
            )  # fmt: skip
        )
    elif died and died < PROBATE_FROM:
        steps.append(
            Step(
                "probate",
                f"from {died}",
                "Before 1858 wills were proved in church courts.",
                [
                    Route(
                        "Wills before 1858",
                        "Record offices and The National Archives",
                        "Wills proved in church courts.",
                        "ask",
                        "Ask the record office which court covered the parish.",
                        checked=False,
                    )
                ],
            )  # fmt: skip
        )
    return steps
