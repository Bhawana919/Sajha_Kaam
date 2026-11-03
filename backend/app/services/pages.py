"""Shared shell for the public, server-rendered pages (both languages, design tokens, no trackers)."""

import html

from fastapi.responses import HTMLResponse


def page(title: str, body: str, scripts: str = "") -> HTMLResponse:
    css = """
    :root{--paper:#F6F4EE;--ink:#252A25;--soft:#5B6058;--brick:#A64C32;--sage:#6B7561;--clay:#EAE5DB;--line:#D5D1C7;--warn:#F6EBCF}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
    font:16px/1.55 "Noto Sans Devanagari","Inter",system-ui,sans-serif}
    main{max-width:560px;margin:0 auto;padding:16px}h1{font-size:26px;line-height:1.35;margin:8px 0}
    .ne{font-family:"Noto Sans Devanagari",system-ui,sans-serif}.soft{color:var(--soft)}
    .card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0}
    .tag{display:inline-block;background:var(--clay);border-radius:8px;padding:2px 8px;font-size:13px;margin:2px 4px 2px 0}
    .ok{background:#E4E8DF;color:var(--sage)}.demo{background:var(--warn);color:#6B4700}
    .level{background:var(--clay);border:1px solid var(--line);border-radius:12px;padding:16px}
    button{font:inherit;min-height:48px;padding:8px 16px;border-radius:10px;border:1px solid var(--line);
    background:var(--brick);color:#fff;cursor:pointer;margin:4px 8px 4px 0}button.quiet{background:#fff;color:var(--ink)}
    .pass{color:#2F6B3F;font-weight:700}.fail{color:var(--brick);font-weight:700}
    table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid var(--line);padding:6px 4px;text-align:left}
    tr.broken td{background:#F3E3DC}.mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;word-break:break-all}
    """
    doc = (f'<!doctype html><html lang="ne"><head><meta charset="utf-8"><meta name="viewport" '
           f'content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{css}</style>'
           f"</head><body><main>{body}</main>{scripts}</body></html>")
    return HTMLResponse(doc)


def not_found() -> HTMLResponse:
    response = page("Not found", '<h1>Not found · <span class="ne">भेटिएन</span></h1>'
                                 '<p class="soft">This link does not exist, has expired or was revoked.<br>'
                                 '<span class="ne">यो लिङ्क छैन, म्याद सकियो वा रद्द गरियो।</span></p>')
    response.status_code = 404
    return response
