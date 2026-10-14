from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from components.settings import DIALOGUE_DIR, LORE_DIR

HEADER = re.compile(r"^::\s*(?P<name>[^\[{]*?)\s*(?:\[(?P<tags>[^\]]*)\])?\s*(?:\{.*\})?\s*$")
LINK = re.compile(r"\[\[(.+?)\]\]")


@dataclass
class Passage:
    name: str
    text: str  # passage text with the link markup removed
    tags: List[str] = field(default_factory=list)
    links: List[Tuple[str, str]] = field(default_factory=list)  # (answer text, target passage)


@dataclass
class Dialogue:
    title: str
    start: str
    passages: Dict[str, Passage]


def parse_link(inner: str) -> Tuple[str, str]:
    if "->" in inner:
        label, target = inner.rsplit("->", 1)
    elif "<-" in inner:
        target, label = inner.split("<-", 1)
    elif "|" in inner:
        label, target = inner.split("|", 1)
    else:
        label = target = inner
    return label.strip(), target.strip()


def parse_twee(source: str) -> Dialogue:
    chunks: List[Tuple[str, List[str]]] = []
    for line in source.splitlines():
        if line.startswith("::"):
            chunks.append((line, []))
        elif chunks:
            chunks[-1][1].append(line)

    title = "Untitled"
    start = "Start"
    passages: Dict[str, Passage] = {}

    for header, body_lines in chunks:
        match = HEADER.match(header)
        if not match:
            continue
        name = match.group("name").strip()
        tags = (match.group("tags") or "").split()
        body = "\n".join(body_lines).strip()

        if name == "StoryTitle":
            title = body
            continue
        if name == "StoryData":
            data = json.loads(body or "{}")
            start = data.get("start", start)
            continue

        links = [parse_link(inner) for inner in LINK.findall(body)]
        text = LINK.sub("", body).strip()
        passages[name] = Passage(name=name, text=text, tags=tags, links=links)

    for passage in passages.values():
        for label, target in passage.links:
            if target not in passages:
                raise ValueError(f"'{passage.name}' links to missing passage '{target}'")
    if start not in passages:
        raise ValueError(f"start passage '{start}' does not exist")

    return Dialogue(title=title, start=start, passages=passages)


def load_dialogue(filename: str) -> Dialogue:
    with open(filename, encoding="utf-8") as f:
        return parse_twee(f.read())


def list_dialogues() -> List[Tuple[str, str]]:
    os.makedirs(DIALOGUE_DIR, exist_ok=True)
    result = []
    for name in sorted(os.listdir(DIALOGUE_DIR)):
        if name.endswith(".twee"):
            result.append((name[: -len(".twee")].replace("_", " "), name))
    return result

def list_lore() -> List[Tuple[str, str]]:
    os.makedirs(LORE_DIR, exist_ok=True)
    result = []
    for name in sorted(os.listdir(LORE_DIR)):
        if name.endswith(".txt"):
            result.append((name[: -len(".txt")].replace("_", " "), name))
    return result

def quest_key(text: str) -> str:
    return text.strip().lower().replace(" ", "_")
