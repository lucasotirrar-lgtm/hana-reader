import requests
from flask import Flask, Response, jsonify, render_template, request


app = Flask(__name__, template_folder="../templates", static_folder="../static")

MANGADEX = "https://api.mangadex.org"
HEADERS = {"User-Agent": "HanaReader/1.1 (+private reader)"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
SESSION.trust_env = False


def clamp_int(value, default, low=1, high=100):
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default


def md_get(path, **params):
    clean = {k: v for k, v in params.items() if v not in ("", None, [])}
    r = SESSION.get(f"{MANGADEX}{path}", params=clean, timeout=12)
    r.raise_for_status()
    return r.json()


def manga_params(limit, offset, order=None):
    params = {
        "limit": limit,
        "offset": offset,
        "includes[]": ["cover_art", "author", "artist"],
        "availableTranslatedLanguage[]": ["pt-br"],
        "contentRating[]": ["safe", "suggestive", "erotica"],
    }
    params.update(order or {"order[followedCount]": "desc"})
    return params


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/manga/<manga_id>")
def manga_detail(manga_id):
    return render_template("manga.html", manga_id=manga_id)


@app.get("/read/<manga_id>/<chapter_id>")
def reader(manga_id, chapter_id):
    return render_template("reader.html", manga_id=manga_id, chapter_id=chapter_id)


@app.get("/api/search")
def search():
    limit = clamp_int(request.args.get("limit"), 20)
    offset = clamp_int(request.args.get("offset"), 0, 0, 10000)
    query = request.args.get("q", "").strip()
    try:
        params = manga_params(limit, offset, {"order[relevance]": "desc"})
        if query:
            params["title"] = query
        return jsonify(md_get("/manga", **params))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.get("/api/browse")
def browse():
    limit = clamp_int(request.args.get("limit"), 20)
    offset = clamp_int(request.args.get("offset"), 0, 0, 10000)
    tag = request.args.get("tag", "").strip()
    letter = request.args.get("letter", "").strip().upper()
    try:
        params = manga_params(limit, offset)
        if tag:
            params["includedTags[]"] = [tag]
        if letter and letter != "ALL":
            params["title"] = letter
        return jsonify(md_get("/manga", **params))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.get("/api/tags")
def tags():
    try:
        return jsonify(md_get("/manga/tag"))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.get("/api/manga/<manga_id>")
def manga_info(manga_id):
    try:
        return jsonify(md_get("/manga/" + manga_id, **{"includes[]": ["cover_art", "author", "artist"]}))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.get("/api/manga/<manga_id>/chapters")
def manga_chapters(manga_id):
    try:
        all_pages = request.args.get("all", "1") != "0"
        limit = 100 if all_pages else clamp_int(request.args.get("limit"), 100)
        offset = clamp_int(request.args.get("offset"), 0, 0, 10000)
        params = {
            "manga": manga_id,
            "translatedLanguage[]": ["pt-br"],
            "order[chapter]": "asc",
            "includes[]": ["scanlation_group"],
            "limit": limit,
            "offset": offset,
        }
        first = md_get("/chapter", **params)
        if not all_pages:
            return jsonify(first)

        chapters = first.get("data", [])
        total = first.get("total", len(chapters))
        while len(chapters) < total:
            params["offset"] = len(chapters)
            batch = md_get("/chapter", **params).get("data", [])
            if not batch:
                break
            chapters.extend(batch)
        first["data"] = chapters
        first["limit"] = len(chapters)
        first["offset"] = 0
        return jsonify(first)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.get("/api/chapter/<chapter_id>")
def chapter_info(chapter_id):
    try:
        return jsonify(md_get("/chapter/" + chapter_id, **{"includes[]": ["manga", "scanlation_group"]}))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.get("/api/chapter/<chapter_id>/pages")
def chapter_pages(chapter_id):
    quality = "data-saver" if request.args.get("quality") == "saver" else "data"
    try:
        data = md_get("/at-home/server/" + chapter_id)
        chapter = data.get("chapter") or {}
        files = chapter.get("dataSaver" if quality == "data-saver" else "data", [])
        pages = [f"{data['baseUrl']}/{quality}/{chapter['hash']}/{name}" for name in files]
        return jsonify({"pages": pages, "total": len(pages), "quality": quality})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.get("/api/cover/<manga_id>/<cover_file>")
def cover(manga_id, cover_file):
    try:
        url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover_file}.256.jpg"
        r = SESSION.get(url, timeout=12)
        r.raise_for_status()
        return Response(r.content, content_type=r.headers.get("content-type", "image/jpeg"))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 404


if __name__ == "__main__":
    app.run(debug=True)
