#!/usr/bin/env python3
"""特教課表產生器：data.json（人看得懂的來源）→ 單檔 HTML 課表。

用法：
  python build.py data.json 輸出.html                  # 產生網頁
  python build.py --from-html 舊課表.html data.json     # 從既有課表網頁反推出 data.json
"""
import json, os, re, sys, io

DAYS = ["一", "二", "三", "四", "五"]
DEFAULT_PERIODS = {
    "早修": ["07:30", "08:10"], "1": ["08:20", "09:05"], "2": ["09:15", "10:00"],
    "3": ["10:15", "11:00"], "4": ["11:10", "11:55"], "午休": ["12:35", "13:20"],
    "5": ["13:20", "14:05"], "6": ["14:15", "15:00"], "7": ["15:15", "16:00"],
}
GROUP_COLORS = [
    "emerald", "amber", "sky", "purple", "orange", "rose", "cyan",
    "indigo", "teal", "yellow", "fuchsia", "lime", "pink", "blue",
]
ROOM_COLORS = [  # (背景, 文字, 邊框)
    ("#dcfce7", "#15803d", "#86efac"), ("#dbeafe", "#1d4ed8", "#93c5fd"),
    ("#fef3c7", "#b45309", "#fcd34d"), ("#f3e8ff", "#7e22ce", "#d8b4fe"),
    ("#fce7f3", "#be185d", "#f9a8d4"), ("#e0f2fe", "#0369a1", "#7dd3fc"),
    ("#ffedd5", "#c2410c", "#fdba74"), ("#ecfccb", "#4d7c0f", "#bef264"),
]


def split_student(s):
    """'702 王小明' → ('702', '王小明')；沒有班級就 ('', 名字)"""
    s = s.strip().strip("()（）").strip()  # 括號只是備註，名字要乾淨才查得到
    m = re.match(r"^(\S+)\s+(.+)$", s)
    return (m.group(1), m.group(2)) if m else ("", s)


def build_data(src):
    warn = []
    days = src.get("days", DAYS)
    pt = src.get("period_times") or DEFAULT_PERIODS
    period_times, period_keys = {}, list(pt.keys())
    for k, v in pt.items():
        start, end = (v if isinstance(v, list) else [v["start"], v["end"]])
        name = k if k in ("早修", "午休") else f"第{k}節"
        period_times[k] = {"start": start, "end": end, "name": name}

    rooms_out = [{"key": r["key"], "short": r.get("short", r["key"]), "label": r.get("label", r["key"])}
                 for r in src["rooms"]]
    room_keys = [r["key"] for r in rooms_out]

    t_names = [t["name"] for t in src["teachers"]]
    slot_count = {n: 0 for n in t_names}
    extra = {s["name"]: s for s in src.get("students", [])}

    groups, schedules, students = {}, [], {}
    color_by_set = {}
    busy = {}  # (種類, 名稱, 星期, 節次) -> 組別
    for g in src["groups"]:
        code, teacher = g["code"], g["teacher"]
        if teacher not in t_names:
            warn.append(f"組別 {code} 的老師「{teacher}」不在 teachers 清單")
        members = [split_student(x) if isinstance(x, str) else (x.get("class", ""), x["name"])
                   for x in g["students"]]
        stu_str = "、".join(f"{c} {n}".strip() for c, n in members)
        headcount = f"{len(members)}人"
        key = frozenset(n for _, n in members)
        if g.get("color_like") and g["color_like"] in groups:
            color = groups[g["color_like"]]["color"]
        elif key in color_by_set:
            color = color_by_set[key]  # 學生名單相同 → 同色
        else:
            c = GROUP_COLORS[len(color_by_set) % len(GROUP_COLORS)]
            color = f"bg-{c}-100 text-{c}-900 border-{c}-300 hover:bg-{c}-200"
            color_by_set[key] = color
        groups[code] = {"code": code, "teacher": teacher, "method": g.get("method", ""),
                        "students": stu_str, "headcount": headcount, "color": color}
        for day, period, room in g["slots"]:
            if day not in days:
                warn.append(f"{code}：星期「{day}」不在 days")
            if period not in period_times:
                warn.append(f"{code}：節次「{period}」不在 period_times")
            if room not in room_keys:
                warn.append(f"{code}：教室「{room}」不在 rooms")
            sess = {"teacher": teacher, "day": day, "period": period, "group": code, "room": room,
                    "method": g.get("method", ""), "students": stu_str, "headcount": headcount}
            schedules.append(sess)
            slot_count[teacher] = slot_count.get(teacher, 0) + 1
            for kind, name in [("老師", teacher), ("教室", room)] + [("學生", n) for _, n in members]:
                k = (kind, name, day, period)
                if k in busy and busy[k] != code:
                    warn.append(f"衝堂：{kind}「{name}」週{day} {period} 同時在 {busy[k]} 與 {code}")
                busy[k] = code
        for c, n in members:
            st = students.setdefault(n, {"name": n, "class": c, "seat": "", "case_teacher": "",
                                         "homeroom_teacher": "", "classes": []})
            if c and not st["class"]:
                st["class"] = c
            for day, period, room in g["slots"]:
                st["classes"].append({"teacher": teacher, "day": day, "period": period, "group": code,
                                      "room": room, "method": g.get("method", ""),
                                      "students": stu_str, "headcount": headcount})
    for n, e in extra.items():
        if n not in students:
            students[n] = {"name": n, "class": e.get("class", ""), "seat": "", "case_teacher": "",
                           "homeroom_teacher": "", "classes": []}
        for f in ("class", "seat", "case_teacher", "homeroom_teacher"):
            if e.get(f):
                students[n][f] = e[f]

    teachers = [{"name": t["name"], "short": t.get("short", ""),
                 "hours": t.get("hours") or f"{slot_count.get(t['name'], 0)}節"} for t in src["teachers"]]
    data = {"title": src.get("title", ""), "subtitle": src.get("subtitle", ""), "days": days,
            "period_keys": period_keys, "period_times": period_times, "teachers": teachers,
            "classrooms": room_keys, "rooms": rooms_out,
            "classroom_labels": {r["key"]: r["label"] for r in rooms_out},
            "groups": groups, "schedules": schedules, "students": students}
    return data, warn


def render(src, tpl):
    data, warn = build_data(src)
    css = "\n    ".join(
        ".room-tag-%d { background: %s; color: %s; border: 1px solid %s; }" % ((i,) + ROOM_COLORS[i % len(ROOM_COLORS)])
        for i in range(len(data["rooms"])))
    css += "\n    .room-tag-x { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }"
    first = next(iter(data["students"].values()), {"name": "王小明", "class": "701"})
    title = src.get("title", "特教課表")
    html = (tpl.replace("{{TITLE}}", title)
               .replace("{{SHORT}}", src.get("short", title[0]))
               .replace("{{SEMESTER}}", src.get("semester", ""))
               .replace("{{EXAMPLE_NAME}}", first["name"])
               .replace("{{EXAMPLE_CLASS}}", first["class"] or "701")
               .replace("/*ROOM_CSS*/", css)
               .replace("/*DATA_JSON*/", json.dumps(data, ensure_ascii=False)))
    return html, warn, data


def from_html(path):
    s = open(path, encoding="utf8").read()
    d = json.loads(re.search(r"const DATA = (\{.*?\});\n", s, re.S).group(1))
    groups = {}
    for sc in d["schedules"]:
        g = groups.setdefault(sc["group"], {"code": sc["group"], "teacher": sc["teacher"],
                                            "method": sc.get("method", ""),
                                            "students": [x for x in sc["students"].split("、") if x], "slots": []})
        g["slots"].append([sc["day"], sc["period"], sc["room"]])
    for code, g in d["groups"].items():  # 有組別但沒排課的也保留
        groups.setdefault(code, {"code": code, "teacher": g["teacher"], "method": g.get("method", ""),
                                 "students": [x for x in g["students"].split("、") if x], "slots": []})
    st = [{"name": v["name"], "class": v.get("class", ""), "seat": v.get("seat", ""),
           "case_teacher": v.get("case_teacher", ""), "homeroom_teacher": v.get("homeroom_teacher", "")}
          for v in d["students"].values()]
    return {"title": re.search(r"<title>(.*?)</title>", s).group(1), "semester": "",
            "period_times": {k: [v["start"], v["end"]] for k, v in d["period_times"].items()},
            "teachers": [{"name": t["name"], "hours": t.get("hours", "")} for t in d["teachers"]],
            "rooms": [{"key": k, "short": k, "label": d["classroom_labels"].get(k, k)} for k in d["classrooms"]],
            "groups": list(groups.values()), "students": st}


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "--from-html":
        with open(a[2], "w", encoding="utf8") as f:
            json.dump(from_html(a[1]), f, ensure_ascii=False, indent=1)
        print("已輸出", a[2])
        sys.exit()
    if len(a) != 2:
        print(__doc__)
        sys.exit(1)
    here = os.path.dirname(os.path.abspath(__file__))
    tpl = open(os.path.join(here, "template.html"), encoding="utf8").read()
    with open(a[0], encoding="utf8") as f:
        src = json.load(f)
    html, warn, data = render(src, tpl)
    with open(a[1], "w", encoding="utf8") as f:
        f.write(html)
    print(f"已產生 {a[1]}：{len(data['groups'])} 組、{len(data['schedules'])} 堂、{len(data['students'])} 位學生")
    for w in warn:
        print("⚠", w)
