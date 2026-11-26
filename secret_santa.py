#!/usr/bin/env python3
"""Create Secret Santa draws and encrypted GitHub Pages reveal links."""
import argparse
import base64
import json
import secrets
import sys
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "participants.json"


def load():
    if not CONFIG.exists():
        return {"participants": [], "exclusions": []}
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def save(data):
    CONFIG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")


def matching(names, excluded):
    """Find a randomized perfect matching, or report impossibility."""
    rng = secrets.SystemRandom()
    order = names[:]
    rng.shuffle(order)
    candidates = {}
    for giver in order:
        candidates[giver] = [recipient for recipient in names
                             if recipient != giver and (giver, recipient) not in excluded]
        rng.shuffle(candidates[giver])
    recipient_to_giver = {}

    def assign(giver, seen):
        for recipient in candidates[giver]:
            if recipient in seen:
                continue
            seen.add(recipient)
            if recipient not in recipient_to_giver or assign(recipient_to_giver[recipient], seen):
                recipient_to_giver[recipient] = giver
                return True
        return False

    for giver in order:
        if not assign(giver, set()):
            raise ValueError("No valid draw exists with these participants and exclusions.")
    return {giver: recipient for recipient, giver in recipient_to_giver.items()}


def b64(data):
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="Add one or more participants")
    add.add_argument("names", nargs="+")
    exclude = sub.add_parser("exclude", help="Exclude both directions between two participants")
    exclude.add_argument("first")
    exclude.add_argument("second")
    unexclude = sub.add_parser("unexclude", help="Remove a mutual exclusion")
    unexclude.add_argument("first")
    unexclude.add_argument("second")
    remove = sub.add_parser("remove", help="Remove a participant and their exclusions")
    remove.add_argument("name")
    sub.add_parser("list", help="Show participants and exclusions")
    draw = sub.add_parser("draw", help="Create an encrypted draw and private master list")
    draw.add_argument("--url", required=True, help="Your HTTPS GitHub Pages URL")
    args = parser.parse_args()
    data = load()
    names = data["participants"]
    exclusions = data["exclusions"]

    if args.command == "add":
        for raw in args.names:
            name = raw.strip()
            if not name or name in names:
                raise ValueError(f"Empty or duplicate participant: {raw!r}")
            names.append(name)
        save(data)
    elif args.command == "remove":
        if args.name not in names:
            raise ValueError("Participant not found.")
        names.remove(args.name)
        data["exclusions"] = [pair for pair in exclusions if args.name not in pair]
        save(data)
    elif args.command in ("exclude", "unexclude"):
        if args.first not in names or args.second not in names or args.first == args.second:
            raise ValueError("Choose two different existing participants.")
        found = next((p for p in exclusions if set(p) == {args.first, args.second}), None)
        if args.command == "exclude":
            if found:
                raise ValueError("That exclusion already exists.")
            exclusions.append([args.first, args.second])
        elif found:
            exclusions.remove(found)
        else:
            raise ValueError("That exclusion does not exist.")
        save(data)
    elif args.command == "list":
        print("Participants:")
        for name in names:
            print(" -", name)
        print("Mutual exclusions:")
        for a, b in exclusions:
            print(f" - {a} <-> {b}")
    elif args.command == "draw":
        if len(names) < 2:
            raise ValueError("Add at least two participants.")
        if not args.url.startswith("https://") or "?" in args.url or "#" in args.url:
            raise ValueError("Use your HTTPS GitHub Pages base URL without a query or fragment.")
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise ValueError("Install dependencies first: python -m pip install -r requirements.txt") from None
        blocked = {(a, b) for a, b in exclusions} | {(b, a) for a, b in exclusions}
        pairs = matching(names, blocked)
        draw_id = secrets.token_hex(16)
        records = {}
        master = {"draw_id": draw_id, "assignments": []}
        for giver in names:
            key = AESGCM.generate_key(bit_length=256)
            nonce = secrets.token_bytes(12)
            record_id = secrets.token_hex(16)
            plaintext = json.dumps({"giver": giver, "recipient": pairs[giver]}, ensure_ascii=False).encode("utf-8")
            ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
            records[record_id] = {"nonce": b64(nonce), "ciphertext": b64(ciphertext)}
            query = urlencode({"draw": draw_id, "id": record_id})
            link = args.url.rstrip("/") + "/?" + query + "#" + b64(key)
            master["assignments"].append({"giver": giver, "recipient": pairs[giver], "link": link})
        private = ROOT / "private"
        public = ROOT / "docs" / "draws"
        private.mkdir(exist_ok=True)
        public.mkdir(parents=True, exist_ok=True)
        master_path = private / (draw_id + ".json")
        public_path = public / (draw_id + ".json")
        master_path.write_text(json.dumps(master, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
        public_path.write_text(json.dumps(records, separators=(",", ":")) + chr(10), encoding="utf-8")
        print("Draw created.")
        print("Private master list and links:", master_path)
        print("Public encrypted data to publish:", public_path)
        print("Publish the docs folder, then send each person only their own link.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, json.JSONDecodeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
