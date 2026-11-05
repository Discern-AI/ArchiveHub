import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from archive.models import Derivative, FileAsset, ProcessingJob
from projects.models import Project, ProjectMember, Role

pytestmark = pytest.mark.django_db


def make_pdf(text: str) -> bytes:
    """A valid one-page PDF with a text layer, built with correct xref offsets."""
    stream = f"BT /F1 18 Tf 20 60 Td ({text}) Tj ET".encode()
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 144]/Contents 4 0 R"
        b"/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length %d>>stream\n" % len(stream) + stream + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF" % (len(objects) + 1, xref)
    return bytes(out)


PDF = make_pdf("Hello Newbury letters")


def jpeg_with_exif() -> bytes:
    img = Image.new("RGB", (1200, 800), "grey")
    exif = Image.Exif()
    exif[0x0132] = "1962:06:01 12:00:00"
    out = io.BytesIO()
    img.save(out, "JPEG", exif=exif)
    return out.getvalue()


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, title="Family papers")


def upload(client, project, name, data, **extra):
    return client.post(
        f"/api/v1/projects/{project.id}/files",
        {"file": SimpleUploadedFile(name, data), **extra},
    )


def test_text_upload_is_checked_and_read(alice_client, project):
    r = upload(alice_client, project, "notes.txt", b"Grandad ran the Pigeons.")
    assert r.status_code == 201, r.content
    f = FileAsset.objects.get()
    assert f.status == "indexed" and len(f.sha256) == 64
    assert "No malware scanner" in f.scan_note  # we say so rather than imply it was scanned
    assert Derivative.objects.get(file=f).text == "Grandad ran the Pigeons."


def test_pdf_text_layer_is_extracted(alice_client, project):
    assert upload(alice_client, project, "letter.pdf", PDF).status_code == 201
    f = FileAsset.objects.get()
    assert f.page_count == 1
    assert "Hello Newbury" in Derivative.objects.get(file=f, kind="text").text


def test_damaged_pdf_fails_clearly(alice_client, project):
    assert upload(alice_client, project, "broken.pdf", b"%PDF-1.4 truncated").status_code == 201
    f = FileAsset.objects.get()
    assert f.status == "failed" and "damaged" in f.status_detail


@pytest.mark.parametrize(
    "name, data, reason",
    [
        ("evil.pdf", b"MZ\x90\x00 not a pdf", "doesn't look like a PDF"),
        ("photo.jpg", b"<html>", "doesn't look like an image"),
        ("tool.exe", b"MZ\x90\x00", "isn't supported"),
        ("empty.txt", b"", "empty"),
        ("tree.ged", b"hello", "GEDCOM"),
    ],
)
def test_bad_uploads_are_rejected(alice_client, project, name, data, reason):
    r = upload(alice_client, project, name, data)
    assert r.status_code == 422 and reason in r.json()["detail"]
    assert not FileAsset.objects.exists()


def test_size_limit(alice_client, project, settings):
    settings.ARCHIVE_MAX_UPLOAD_MB = 0
    r = upload(alice_client, project, "big.txt", b"x" * 10)
    assert r.status_code == 422 and "up to" in r.json()["detail"]


def test_image_gets_a_preview_without_exif(alice_client, project):
    assert upload(alice_client, project, "cheap-street.jpg", jpeg_with_exif()).status_code == 201
    f = FileAsset.objects.get()
    assert f.status == "needs_processing"
    assert f.metadata["camera_date"] == "1962:06:01 12:00:00"
    r = alice_client.get(f"/api/v1/files/{f.id}/preview")
    assert r["Content-Type"] == "image/jpeg"
    thumb = Image.open(io.BytesIO(r.content))
    assert max(thumb.size) <= 640 and not thumb.getexif()


def test_handwriting_needs_confirmation_and_records_the_engine(alice_client, project, monkeypatch):
    monkeypatch.setattr("archive.htr.transcribe", lambda f, data: ("Dear Mum [?]", "claude-test"))
    upload(alice_client, project, "letter.jpg", jpeg_with_exif())
    f = FileAsset.objects.get()
    r = alice_client.post(
        f"/api/v1/files/{f.id}/jobs", {"kind": "handwriting"}, content_type="application/json"
    )
    job = r.json()
    assert job["status"] == "awaiting_confirmation" and job["estimate_credits"] == 2
    assert not Derivative.objects.filter(method="ai_handwriting").exists()  # nothing ran yet

    r = alice_client.post(f"/api/v1/jobs/{job['id']}/confirm")
    assert r.json()["status"] == "done" and r.json()["credits_used"] == 2
    d = Derivative.objects.get(method="ai_handwriting")
    assert d.text == "Dear Mum [?]" and d.engine == "claude-test" and "Check it" in d.note
    detail = alice_client.get(f"/api/v1/files/{f.id}").json()
    assert {t["method"] for t in detail["texts"]} == {"ai_handwriting"}
    assert alice_client.post(f"/api/v1/jobs/{job['id']}/confirm").status_code == 409


def test_cancelled_job_never_runs(alice_client, project):
    upload(alice_client, project, "letter.jpg", jpeg_with_exif())
    f = FileAsset.objects.get()
    job = alice_client.post(
        f"/api/v1/files/{f.id}/jobs", {"kind": "handwriting"}, content_type="application/json"
    ).json()
    assert alice_client.post(f"/api/v1/jobs/{job['id']}/cancel").json()["status"] == "cancelled"
    assert alice_client.post(f"/api/v1/jobs/{job['id']}/confirm").status_code == 409


def test_ocr_says_plainly_when_not_installed(alice_client, project, monkeypatch):
    monkeypatch.setattr("archive.processing.shutil.which", lambda name: None)
    upload(alice_client, project, "page.png", _png())
    f = FileAsset.objects.get()
    job = alice_client.post(
        f"/api/v1/files/{f.id}/jobs", {"kind": "ocr"}, content_type="application/json"
    ).json()
    done = alice_client.post(f"/api/v1/jobs/{job['id']}/confirm").json()
    assert done["status"] == "failed" and "isn't installed" in done["error"]
    assert done["credits_used"] == 0


def _png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(out, "PNG")
    return out.getvalue()


def test_download_is_an_attachment_and_unchanged(alice_client, project):
    data = b"Original words."
    upload(alice_client, project, "notes.txt", data)
    f = FileAsset.objects.get()
    r = alice_client.get(f"/api/v1/files/{f.id}/original")
    assert b"".join(r.streaming_content) == data
    assert "attachment" in r["Content-Disposition"]
    assert r["X-Content-Type-Options"] == "nosniff"


def test_files_are_private_to_the_project(alice_client, project, bob, bob_client):
    upload(alice_client, project, "notes.txt", b"private")
    f = FileAsset.objects.get()
    assert bob_client.get(f"/api/v1/projects/{project.id}/files").status_code == 404
    assert bob_client.get(f"/api/v1/files/{f.id}").status_code == 404
    assert bob_client.get(f"/api/v1/files/{f.id}/original").status_code == 404
    assert upload(bob_client, project, "x.txt", b"x").status_code == 404
    ProjectMember.objects.create(project=project, user=bob, role=Role.VIEWER)
    assert bob_client.get(f"/api/v1/files/{f.id}").status_code == 200
    assert upload(bob_client, project, "x.txt", b"x").status_code == 404  # viewers can't add
    assert bob_client.delete(f"/api/v1/files/{f.id}").status_code == 404


def test_assistant_searches_only_files_the_user_can_see(alice_client, project, alice, bob):
    import json

    from assistant.tools import ToolKit

    upload(alice_client, project, "notes.txt", b"Grandad kept pigeons behind the pub.")
    mine = json.loads(ToolKit(user=alice).run("search_archive", {"query": "pigeons pub"})[0])
    assert [r["file"] for r in mine["results"]] == ["notes.txt"]
    theirs = json.loads(ToolKit(user=bob).run("search_archive", {"query": "pigeons pub"})[0])
    assert theirs["results"] == []


def test_folders_and_delete(alice_client, project):
    folder = alice_client.post(
        f"/api/v1/projects/{project.id}/folders",
        {"name": "Letters"},
        content_type="application/json",
    ).json()
    upload(alice_client, project, "a.txt", b"a", folder_id=folder["id"])
    upload(alice_client, project, "b.txt", b"b")
    listed = alice_client.get(
        f"/api/v1/projects/{project.id}/files?folder_id={folder['id']}"
    ).json()
    assert [f["name"] for f in listed] == ["a.txt"]
    f = FileAsset.objects.get(name="a.txt")
    path = f.original.path
    assert alice_client.delete(f"/api/v1/files/{f.id}").status_code == 204
    assert not FileAsset.objects.filter(pk=f.pk).exists()
    import os

    assert not os.path.exists(path)
    assert ProcessingJob.objects.filter(file_id=f.pk).count() == 0
