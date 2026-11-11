import io
import json
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from archive.models import FileAsset
from history.models import LivingStatus, Person
from projects.models import Project
from publishing.models import PageStatus, Post, Redirect
from publishing.render import render

pytestmark = pytest.mark.django_db


def jpeg_with_gps() -> bytes:
    img = Image.new("RGB", (900, 600), "grey")
    exif = Image.Exif()
    exif[0x0132] = "1962:06:01 12:00:00"
    exif[0x8825] = {1: "N", 2: (51.0, 24.0, 0.0)}  # GPS location
    out = io.BytesIO()
    img.save(out, "JPEG", exif=exif)
    return out.getvalue()


@pytest.fixture
def project(alice):
    return Project.objects.create(owner=alice, title="Family papers")


@pytest.fixture
def home(alice_client):
    r = alice_client.put(
        "/api/v1/home",
        {"slug": "Jane's History", "title": "Jane's history", "live": True},
        content_type="application/json",
    )
    assert r.status_code == 200, r.content
    return r.json()


def new_post(client, **fields):
    r = client.post("/api/v1/home/posts", fields, content_type="application/json")
    assert r.status_code == 201, r.content
    return r.json()


def picture(client, project) -> FileAsset:
    r = client.post(
        f"/api/v1/projects/{project.id}/files",
        {"file": SimpleUploadedFile("mill.jpg", jpeg_with_gps())},
    )
    assert r.status_code == 201, r.content
    return FileAsset.objects.get(name="mill.jpg")


# Rendering


def test_render_escapes_html_and_keeps_only_safe_links():
    html = render(
        "## Hi <script>alert(1)</script>\n\n**bold** and [ok](https://example.org) "
        "[bad](javascript:alert(1)) <img src=x onerror=alert(1)>",
        lambda _id: None,
    )
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "<img" not in html
    assert '<a href="https://example.org"' in html
    assert "javascript:" not in html.split("<a ")[-1].split(">")[0]
    assert "<strong>bold</strong>" in html and "<h2>" in html


def test_render_quotes_and_lists_and_drops_unattached_pictures():
    html = render(
        "> said\n> she\n\n- one\n- two\n\n![x](image:00000000-0000-0000-0000-000000000000)",
        lambda _id: None,
    )
    assert "<blockquote>" in html and html.count("<li>") == 2 and "<figure>" not in html


# Homepage


def test_homepage_address_rules(alice_client, bob_client, home):
    assert home["slug"] == "janes-history" and home["url"] == "/h/janes-history/"
    r = bob_client.put(
        "/api/v1/home", {"slug": "janes-history", "title": "Bob"}, content_type="application/json"
    )
    assert r.status_code == 409
    r = bob_client.put(
        "/api/v1/home", {"slug": "api", "title": "Bob"}, content_type="application/json"
    )
    assert r.status_code == 422


def test_nothing_is_public_until_published_and_switched_on(alice_client, home):
    p = new_post(alice_client, title="The mill", body="It burned in 1887.")
    anon = Client()
    assert anon.get(f"/h/janes-history/{p['slug']}/").status_code == 404
    r = alice_client.post(
        f"/api/v1/home/posts/{p['id']}/publish", {}, content_type="application/json"
    )
    assert r.status_code == 200, r.content
    page = anon.get(f"/h/janes-history/{p['slug']}/")
    assert page.status_code == 200 and b"It burned in 1887." in page.content
    assert b"The mill" in anon.get("/h/janes-history/").content
    alice_client.put(
        "/api/v1/home", {"slug": "janes-history", "title": "Jane", "live": False},
        content_type="application/json",
    )  # fmt: skip
    assert anon.get(f"/h/janes-history/{p['slug']}/").status_code == 404
    assert anon.get("/h/janes-history/").status_code == 404


def test_editing_a_published_post_takes_it_back_to_draft(alice_client, home):
    p = new_post(alice_client, title="The mill", body="It burned.")
    alice_client.post(f"/api/v1/home/posts/{p['id']}/publish", {}, content_type="application/json")
    r = alice_client.patch(
        f"/api/v1/home/posts/{p['id']}", {"title": "The mill", "body": "Rebuilt."},
        content_type="application/json",
    )  # fmt: skip
    assert r.json()["status"] == PageStatus.DRAFT


def test_other_people_cannot_touch_your_posts(alice_client, bob_client, home):
    p = new_post(alice_client, title="Mine", body="Words.")
    assert bob_client.get(f"/api/v1/home/posts/{p['id']}").status_code == 404
    r = bob_client.post(
        f"/api/v1/home/posts/{p['id']}/publish", {}, content_type="application/json"
    )
    assert r.status_code == 404


# The check


def test_living_person_named_needs_confirmation(alice_client, home, project):
    Person.objects.create(project=project, name="Mary Smith", living_status=LivingStatus.UNKNOWN)
    Person.objects.create(project=project, name="Old Tom Smith", living_status="deceased")
    p = new_post(alice_client, title="Visit", body="Mary Smith and Old Tom Smith went.")
    check = alice_client.post(f"/api/v1/home/posts/{p['id']}/check").json()
    assert check["ok"] and [w["kind"] for w in check["warnings"]] == ["living"]
    url = f"/api/v1/home/posts/{p['id']}/publish"
    assert alice_client.post(url, {}, content_type="application/json").status_code == 409
    r = alice_client.post(url, {"confirm_warnings": True}, content_type="application/json")
    assert r.status_code == 200 and r.json()["approved_check"]["warnings"]
    assert Post.objects.get().approved_by.email == "alice@example.com"


def test_pictures_need_rights_and_credit(alice_client, home, project):
    f = picture(alice_client, project)
    p = new_post(alice_client, title="Mill", body="Words.")
    base = f"/api/v1/home/posts/{p['id']}"
    r = alice_client.post(f"{base}/images", {"file_id": str(f.id)}, content_type="application/json")
    md = r.json()["markdown"]
    alice_client.patch(base, {"title": "Mill", "body": f"Words.\n\n{md}"},
                       content_type="application/json")  # fmt: skip
    check = alice_client.post(f"{base}/check").json()
    assert not check["ok"] and check["blockers"][0]["kind"] == "rights"
    assert any(w["kind"] == "private" for w in check["warnings"])
    assert (
        alice_client.post(f"{base}/publish", {}, content_type="application/json").status_code == 422
    )
    alice_client.post(f"{base}/images", {"file_id": str(f.id), "rights": "permission"},
                      content_type="application/json")  # fmt: skip
    assert alice_client.post(f"{base}/check").json()["blockers"][0]["kind"] == "credit"
    alice_client.post(
        f"{base}/images",
        {"file_id": str(f.id), "rights": "permission", "credit": "West Berkshire Museum"},
        content_type="application/json",
    )
    r = alice_client.post(f"{base}/publish", {"confirm_warnings": True},
                          content_type="application/json")  # fmt: skip
    assert r.status_code == 200, r.content
    page = Client().get(f"/h/janes-history/{p['slug']}/")
    assert b"West Berkshire Museum" in page.content and b"<figure>" in page.content


def test_picture_served_from_preview_without_camera_data(alice_client, home, project):
    f = picture(alice_client, project)
    p = new_post(alice_client, title="Mill", body="Words.")
    base = f"/api/v1/home/posts/{p['id']}"
    alice_client.post(f"{base}/images", {"file_id": str(f.id), "rights": "own"},
                      content_type="application/json")  # fmt: skip
    anon = Client()
    assert anon.get(f"/h/janes-history/images/{f.id}").status_code == 404  # not published yet
    alice_client.post(f"{base}/publish", {"confirm_warnings": True},
                      content_type="application/json")  # fmt: skip
    r = anon.get(f"/h/janes-history/images/{f.id}")
    assert r.status_code == 200
    img = Image.open(io.BytesIO(r.content))
    assert max(img.size) <= 640 and not img.getexif().get_ifd(0x8825)
    alice_client.post(f"{base}/unpublish")
    assert anon.get(f"/h/janes-history/images/{f.id}").status_code == 404


def test_unattached_picture_blocks(alice_client, home):
    p = new_post(alice_client, title="Mill",
                 body="Words.\n\n![x](image:00000000-0000-0000-0000-000000000000)")  # fmt: skip
    check = alice_client.post(f"/api/v1/home/posts/{p['id']}/check").json()
    assert [b["kind"] for b in check["blockers"]] == ["image"]


# WordPress


WXR = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"
  xmlns:wp="http://wordpress.org/export/1.2/" xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/">
<channel><title>Old blog</title><wp:wxr_version>1.2</wp:wxr_version>
<item><title>The Mill Fire</title><link>https://janeblog.example/2019/05/the-mill-fire/</link>
<pubDate>Wed, 01 May 2019 10:00:00 +0000</pubDate><wp:post_name>the-mill-fire</wp:post_name>
<wp:post_type>post</wp:post_type><wp:status>publish</wp:status>
<excerpt:encoded><![CDATA[A fire.]]></excerpt:encoded>
<content:encoded><![CDATA[<p>It <strong>burned</strong>.</p><script>x()</script>
<p><img src="https://janeblog.example/mill.jpg" alt="The mill"></p>
<p><a href="https://example.org/a">source</a></p>]]></content:encoded></item>
<item><title>About</title><link>https://janeblog.example/about/</link>
<wp:post_type>page</wp:post_type><wp:status>publish</wp:status></item>
</channel></rss>"""


def test_wordpress_import_makes_drafts_and_redirects(alice_client, home):
    r = alice_client.post(
        "/api/v1/home/import/wordpress", {"file": SimpleUploadedFile("blog.xml", WXR)}
    )
    assert r.status_code == 200, r.content
    out = r.json()
    assert out["count"] == 1 and out["skipped"] == 1 and out["images_not_copied"] == 1
    p = Post.objects.get()
    assert p.status == PageStatus.DRAFT and p.source == "wordpress"
    assert "**burned**" in p.body and "[source](https://example.org/a)" in p.body
    assert "Picture not copied across: The mill" in p.body
    assert p.original_url == "https://janeblog.example/2019/05/the-mill-fire/"
    assert p.first_published.year == 2019
    assert Redirect.objects.get().old_path == "/2019/05/the-mill-fire/"
    anon = Client()
    assert anon.get("/h/janes-history/2019/05/the-mill-fire/").status_code == 404  # draft
    alice_client.post(f"/api/v1/home/posts/{p.id}/publish", {}, content_type="application/json")
    r = anon.get("/h/janes-history/2019/05/the-mill-fire/")
    assert r.status_code == 301 and r["Location"] == "/h/janes-history/the-mill-fire/"
    page = anon.get("/h/janes-history/the-mill-fire/")
    assert b'rel="canonical" href="https://janeblog.example/2019/05/the-mill-fire/"' in page.content
    assert b"<script>x()" not in page.content


def test_wordpress_import_rejects_other_files(alice_client, home):
    r = alice_client.post(
        "/api/v1/home/import/wordpress", {"file": SimpleUploadedFile("x.xml", b"<rss></rss>")}
    )
    assert r.status_code == 422


# Social and export


def test_social_posts_fit_and_need_publishing(alice_client, home):
    p = new_post(alice_client, title="T" * 400, body="Words " * 200)
    url = f"/api/v1/home/posts/{p['id']}/social"
    assert alice_client.get(url).status_code == 409
    alice_client.post(f"/api/v1/home/posts/{p['id']}/publish", {}, content_type="application/json")
    out = alice_client.get(url).json()
    assert len(out["posts"][0]["text"]) <= 280 and out["link"] in out["posts"][1]["text"]


def test_export_has_everything(alice_client, home, project):
    f = picture(alice_client, project)
    p = new_post(alice_client, title="Mill", body="Words.")
    alice_client.post(f"/api/v1/home/posts/{p['id']}/images", {"file_id": str(f.id)},
                      content_type="application/json")  # fmt: skip
    r = alice_client.get("/api/v1/home/export")
    assert r.status_code == 200 and r["Content-Type"] == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(z.namelist())
    assert {"homepage.json", "redirects.csv", "README.txt", f"posts/{p['slug']}.md"} <= names
    assert any(n.startswith("images/") for n in names)
    meta = json.loads(z.read(f"posts/{p['slug']}.json"))
    assert meta["images"][0]["rights"] == "unclear"


# Chat drafts


def test_chat_can_draft_but_not_publish(alice, alice_client, home):
    from assistant.tools import ToolKit

    out, error = ToolKit(user=alice).run(
        "draft_post", {"title": "The mill fire", "body": "It burned in 1887."}
    )
    assert not error
    p = Post.objects.get()
    assert p.status == PageStatus.DRAFT and p.source == "chat"
    assert f"/homepage/posts/{p.id}" in out
    assert Client().get(f"/h/janes-history/{p.slug}/").status_code == 404


def test_chat_draft_without_homepage(alice):
    from assistant.tools import ToolKit

    out, error = ToolKit(user=alice).run("draft_post", {"title": "T", "body": "B"})
    assert not error and '"saved": false' in out and not Post.objects.exists()


def test_address_follows_title_until_first_published(alice_client, home):
    p = new_post(alice_client, title="Untitled")
    url = f"/api/v1/home/posts/{p['id']}"
    r = alice_client.patch(url, {"title": "The mill", "body": "It burned."},
                           content_type="application/json")  # fmt: skip
    assert r.json()["slug"] == "the-mill"
    alice_client.post(f"{url}/publish", {}, content_type="application/json")
    r = alice_client.patch(url, {"title": "The mill fire", "body": "It burned."},
                           content_type="application/json")  # fmt: skip
    assert r.json()["slug"] == "the-mill"
