"""Бодит Facebook Page руу Graph API-аар пост нийтлэх.

FB_PAGE_ID, FB_PAGE_ACCESS_TOKEN хоёул тохируулагдсан үед л идэвхжинэ.
Тохируулаагүй бол админ доторх локал загвар хэвээр ажиллана."""
import os

import httpx

PAGE_ID = os.environ.get("FB_PAGE_ID", "").strip()
PAGE_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "").strip()
_VERSION = os.environ.get("FB_GRAPH_VERSION", "").strip()  # хоосон бол апп-ын үндсэн хувилбар
GRAPH = "https://graph.facebook.com" + (f"/{_VERSION}" if _VERSION else "")


def enabled() -> bool:
    return bool(PAGE_ID and PAGE_TOKEN)


def publish(caption: str) -> dict:
    """Page-ийн feed-д текст пост нийтэлнэ. {'id': ..., 'url': ...} эсвэл {'error': ...} буцаана."""
    try:
        r = httpx.post(f"{GRAPH}/{PAGE_ID}/feed", data={"message": caption, "access_token": PAGE_TOKEN}, timeout=30)
        body = r.json()
    except Exception as e:  # noqa: BLE001 — сүлжээний алдааг админд харуулна
        return {"error": f"{type(e).__name__}: {e}"}
    if r.status_code != 200 or "id" not in body:
        err = body.get("error", {}) if isinstance(body, dict) else {}
        return {"error": err.get("message") or f"HTTP {r.status_code}"}
    return {"id": body["id"], "url": f"https://www.facebook.com/{body['id']}"}
