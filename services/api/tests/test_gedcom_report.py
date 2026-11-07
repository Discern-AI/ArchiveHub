from genealogy.gedcom import parse
from genealogy.report import import_report

GED = """0 HEAD
1 SOUR Ancestry.com Family Trees
1 GEDC
2 VERS 5.5.1
0 @I1@ INDI
1 NAME Ann /Example/
1 BIRT
2 DATE 1850
2 SOUR @S1@
1 RESI
2 PLAC Newbury
1 RESI
2 PLAC Reading
1 _MILT Royal Berkshire Regiment
1 OBJE
2 FILE C:/Users/someone/Pictures/ann.jpg
1 NOTE A note
0 @F1@ FAM
1 HUSB @I1@
1 DIV
0 @S1@ SOUR
1 TITL 1851 England Census
0 TRLR
"""


def test_report_says_what_was_left_behind():
    r = import_report(parse(GED))
    assert r["gedcom_version"] == "5.5.1" and r["made_by"] == "Ancestry.com Family Trees"
    assert r["other_facts_not_imported"] == {
        "residences": 2,
        "military service (non-standard tag)": 1,
        "divorces": 1,
    }
    assert r["source_citations_not_imported"] == 1 and r["source_records_not_imported"] == 1
    assert r["media_references"] == 1 and r["media_files_named"] == 1 and r["media_note"]
    assert r["notes_not_imported"] == 1
