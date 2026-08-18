#!/usr/bin/env python
"""Bulk seed HyperKitty archives for local UI development.

Ported from the HyperKitty fork's scripts/seed_dev_data.py (itself adapted from
this repo). Creates threaded discussions with distinct participants, votes,
tags, favorites, attachments, last-views, sender IDs, and a demo login user.
"""

import argparse
import hashlib
import os
import random
import sys
import uuid
from datetime import timedelta
from email.message import EmailMessage
from urllib.error import HTTPError

import django
from mailmanclient import MailmanConnectionError

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from allauth.account.models import EmailAddress  # noqa: E402
from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.sites.models import Site  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402
from django_mailman3.lib.mailman import get_mailman_client  # noqa: E402

from hyperkitty.lib.analysis import compute_thread_order_and_depth  # noqa: E402
from hyperkitty.lib.incoming import DuplicateMessage, add_to_list  # noqa: E402
from hyperkitty.lib.mailman import import_list_from_mailman  # noqa: E402
from hyperkitty.models import (  # noqa: E402
    ArchivePolicy,
    Email,
    Favorite,
    LastView,
    MailingList,
    Sender,
    Tag,
    Tagging,
    Thread,
)

SAMPLE_TOPICS = [
    "Proposal for library feature X",
    "Meeting notes and action items",
    "Question about implementation details",
    "RFC: update the review process",
    "Bug report: regression in latest release",
    "Weekly status update",
    "Call for comments on draft specification",
    "Reminder: upcoming deadline",
    "Summary of mailing list discussion",
    "Patch available for testing",
]

SAMPLE_NAMES = [
    ("Alice Chen", "alice@example.com"),
    ("Bob Martinez", "bob@example.com"),
    ("Carol Nguyen", "carol@example.com"),
    ("David Kim", "david@example.com"),
    ("Elena Rossi", "elena@example.com"),
    ("Frank O'Brien", "frank@example.com"),
    ("Grace Patel", "grace@example.com"),
    ("Henry Wilson", "henry@example.com"),
    ("Iris Johnson", "iris@example.com"),
    ("James Lopez", "james@example.com"),
    ("Karen Schmidt", "karen@example.com"),
    ("Leo Thompson", "leo@example.com"),
]

SAMPLE_TAGS = [
    "rfc",
    "bug",
    "patch",
    "meeting",
    "question",
    "announcement",
    "design",
    "performance",
]

LIST_META = {
    "delegates": ("Delegates", "Official WG delegates discussion"),
    "paper-reviews": ("Paper Reviews", "Review threads for submitted papers"),
    "general": ("General", "General discussion"),
    "dev": ("Development", "Implementation and tooling talk"),
    "announce": ("Announcements", "Low-volume announcements"),
    "cpp": ("C++", "Language and library topics"),
    "boost": ("Boost", "Boost libraries discussion"),
    "test": ("Test", "Sandbox list for UI experiments"),
    "committee": ("Committee (Private)", "Private working-group discussion"),
    "idle": ("Idle", "Archived list with no recent activity"),
}

# Local parts (without @domain) used to exercise HyperKitty index filters.
PRIVATE_LIST_PARTS = frozenset({"committee"})
INACTIVE_LIST_PARTS = frozenset({"idle"})

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo"
DEMO_EMAIL = "demo@example.com"
DEMO_NAME = "Demo User"


def stable_mailman_id(email: str) -> str:
    """Fallback id when Mailman Core is unavailable."""
    digest = hashlib.sha1(email.encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))


def ensure_mailman_user(email: str, display_name: str) -> str:
    """Create/fetch a Mailman user and return its user_id."""
    try:
        client = get_mailman_client()
        try:
            mm_user = client.get_user(email)
        except HTTPError as exc:
            if exc.code != 404:
                raise
            mm_user = client.create_user(email, display_name)
        # Ensure the preferred address is verified for sync/login.
        for address in mm_user.addresses:
            if str(address) == email and not address.verified:
                address.verify()
        return str(mm_user.user_id)
    except (HTTPError, MailmanConnectionError, OSError) as exc:
        print(f"  ! Mailman unavailable for {email}: {exc}")
        return stable_mailman_id(email)


def ensure_users() -> list:
    User = get_user_model()
    users = []
    for name, email in SAMPLE_NAMES:
        username = email.split("@", 1)[0].replace("'", "").replace(".", "")
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": name.split()[0],
                "last_name": " ".join(name.split()[1:]),
            },
        )
        if created:
            user.set_password("password")
            user.save()
        EmailAddress.objects.update_or_create(
            user=user,
            email=email,
            defaults={"verified": True, "primary": True},
        )
        profile = user.hyperkitty_profile
        profile.karma = random.randint(1, 40)
        profile.save(update_fields=["karma"])
        users.append(user)

    demo, created = User.objects.get_or_create(
        username=DEMO_USERNAME,
        defaults={
            "email": DEMO_EMAIL,
            "first_name": "Demo",
            "last_name": "User",
            "is_staff": True,
            "is_superuser": True,
        },
    )
    demo.set_password(DEMO_PASSWORD)
    if not demo.is_superuser:
        demo.is_superuser = True
    demo.save()
    EmailAddress.objects.update_or_create(
        user=demo,
        email=DEMO_EMAIL,
        defaults={"verified": True, "primary": True},
    )
    demo.hyperkitty_profile.karma = 25
    demo.hyperkitty_profile.save(update_fields=["karma"])
    users.append(demo)
    return users


def list_local_part(list_addr: str) -> str:
    return list_addr.split("@", 1)[0]


def configure_mailman_archive_policy(list_addr: str, policy: str) -> None:
    """Best-effort mirror of archive_policy into Mailman Core."""
    try:
        mm_list = get_mailman_client().get_list(list_addr)
    except (HTTPError, MailmanConnectionError, OSError) as exc:
        print(f"  ! Could not set archive_policy={policy} on {list_addr}: {exc}")
        return
    try:
        mm_list.settings["archive_policy"] = policy
        mm_list.save()
    except (HTTPError, MailmanConnectionError, OSError) as exc:
        print(f"  ! Mailman rejected archive_policy={policy} on {list_addr}: {exc}")


def mark_list_private(list_addr: str, users: list | None = None) -> None:
    """Ensure HyperKitty treats the list as private (index hide-switch demo)."""
    configure_mailman_archive_policy(list_addr, "private")
    try:
        mlist = MailingList.objects.get(name=list_addr)
    except MailingList.DoesNotExist:
        return
    mlist.archive_policy = ArchivePolicy.private.value
    mlist.save(update_fields=["archive_policy"])
    if users is None:
        return
    demo = next((u for u in users if u.username == DEMO_USERNAME), None)
    if demo is None:
        return
    try:
        mm_list = get_mailman_client().get_list(list_addr)
        mm_list.subscribe(demo.email)
    except (HTTPError, MailmanConnectionError, OSError) as exc:
        print(f"  ! Could not subscribe {demo.email} to {list_addr}: {exc}")


def decorate_mailing_list(list_addr: str) -> None:
    list_name = list_local_part(list_addr)
    display, description = LIST_META.get(
        list_name, (list_name.title(), f"Archive for {list_addr}")
    )
    mlist = MailingList.objects.get(name=list_addr)
    mlist.display_name = display
    mlist.description = description
    mlist.subject_prefix = f"[{list_name}] "
    mlist.save()


def ensure_inactive_list(list_addr: str) -> None:
    """Register a list in HyperKitty with no threads (inactive filter demo)."""
    import_list_from_mailman(list_addr)
    decorate_mailing_list(list_addr)


def authors_for_thread(msg_count: int) -> list[tuple[str, str]]:
    """Pick distinct participants for a thread, always including the demo user."""
    pool = SAMPLE_NAMES[:]
    random.shuffle(pool)
    needed = min(msg_count, len(pool) + 1)
    authors = [(DEMO_NAME, DEMO_EMAIL)]
    for person in pool:
        if len(authors) >= needed:
            break
        authors.append(person)
    random.shuffle(authors)
    # Ensure replies cycle through participants instead of repeating one author.
    while len(authors) < msg_count:
        authors.append(random.choice(authors))
    return authors[:msg_count]


def build_message(
    list_addr: str,
    thread_idx: int,
    msg_idx: int,
    parent_msg_idx: int | None,
    base_time,
    topic: str,
    author: tuple[str, str],
    with_attachment: bool,
) -> EmailMessage:
    name, addr = author
    msg = EmailMessage()
    list_name, list_domain = list_addr.split("@", 1)
    msg_id = f"<{list_name}-t{thread_idx}-m{msg_idx}@{list_domain}>"
    msg["From"] = f"{name} <{addr}>"
    msg["To"] = list_addr
    if msg_idx == 0:
        msg["Subject"] = f"[{list_name}] {topic} (thread {thread_idx + 1})"
    else:
        msg["Subject"] = f"Re: [{list_name}] {topic} (thread {thread_idx + 1})"
    msg["Message-ID"] = msg_id
    if parent_msg_idx is not None:
        parent_id = f"<{list_name}-t{thread_idx}-m{parent_msg_idx}@{list_domain}>"
        msg["In-Reply-To"] = parent_id
        msg["References"] = parent_id
    sent_at = base_time + timedelta(
        days=thread_idx % 20,
        hours=(thread_idx * 3 + msg_idx) % 24,
        minutes=msg_idx * 11,
    )
    msg["Date"] = sent_at.strftime("%a, %d %b %Y %H:%M:%S +0000")

    paragraphs = random.randint(2, 5)
    body_lines = [
        f"Message {msg_idx + 1} in thread {thread_idx + 1} on {list_addr}.",
        "",
    ]
    if msg_idx > 0:
        body_lines.extend(
            [
                f"> On thread {thread_idx + 1}, earlier writers said:",
                f"> Lorem ipsum dolor sit amet (quoted from message {parent_msg_idx + 1}).",
                "",
            ]
        )
    for p in range(paragraphs):
        body_lines.append(
            f"Paragraph {p + 1}: Lorem ipsum dolor sit amet, consectetur adipiscing "
            f"elit. Integer posuere erat a ante venenatis dapibus posuere velit aliquet. "
            f"Thread {thread_idx + 1}, message {msg_idx + 1}."
        )
        body_lines.append("")
    if "patch" in topic.lower() or "bug" in topic.lower():
        body_lines.extend(
            [
                "```",
                "@@ -12,6 +12,9 @@ void example()",
                "     auto x = compute();",
                "+    // seed discussion patch",
                "+    x.normalize();",
                "     return x;",
                "```",
                "",
            ]
        )
    msg.set_content("\n".join(body_lines))

    if with_attachment:
        patch = (
            f"--- a/example.cpp\n+++ b/example.cpp\n"
            f"@@ thread {thread_idx + 1} message {msg_idx + 1} @@\n"
            f"+// seeded attachment for UI testing\n"
        ).encode("utf-8")
        msg.add_attachment(
            patch,
            maintype="text",
            subtype="x-diff",
            filename=f"thread-{thread_idx + 1}-msg-{msg_idx + 1}.patch",
        )
    return msg


def seed_list(list_addr: str, threads: int, replies: int) -> tuple[int, int]:
    created = 0
    skipped = 0
    # Keep discussions inside the overview "recent" window (~32 days).
    base_time = timezone.now() - timedelta(days=25)
    for thread_idx in range(threads):
        topic = random.choice(SAMPLE_TOPICS)
        authors = authors_for_thread(replies)
        for msg_idx in range(replies):
            if msg_idx == 0:
                parent_msg_idx = None
            elif msg_idx <= 2 or random.random() < 0.55:
                parent_msg_idx = 0
            else:
                parent_msg_idx = random.randint(0, msg_idx - 1)
            with_attachment = msg_idx > 0 and random.random() < 0.12
            msg = build_message(
                list_addr,
                thread_idx,
                msg_idx,
                parent_msg_idx,
                base_time,
                topic,
                authors[msg_idx],
                with_attachment,
            )
            try:
                add_to_list(list_addr, msg, from_import=True)
                created += 1
            except DuplicateMessage:
                skipped += 1
    decorate_mailing_list(list_addr)
    return created, skipped


def link_senders() -> int:
    """Create Mailman users for every sender and store their user ids."""
    linked = 0
    name_by_address = {email: name for name, email in SAMPLE_NAMES}
    name_by_address[DEMO_EMAIL] = DEMO_NAME
    for sender in Sender.objects.all():
        display = name_by_address.get(sender.address) or sender.name
        mailman_id = ensure_mailman_user(sender.address, display)
        if sender.mailman_id != mailman_id:
            sender.mailman_id = mailman_id
            sender.save(update_fields=["mailman_id"])
            linked += 1
    return linked


def enrich_discussions(list_addr: str, users: list) -> dict[str, int]:
    stats = {"votes": 0, "tags": 0, "favorites": 0, "last_views": 0}
    demo = next(u for u in users if u.username == DEMO_USERNAME)
    threads = list(
        Thread.objects.filter(mailinglist__name=list_addr).prefetch_related(
            "emails"
        )
    )
    for thread in threads:
        emails = list(thread.emails.order_by("date"))
        if not emails:
            continue

        # Popular tab needs votes_total > 0 on some threads.
        if random.random() < 0.55:
            for email in random.sample(emails, k=min(len(emails), random.randint(1, 3))):
                for user in random.sample(users, k=random.randint(1, min(4, len(users)))):
                    email.vote(random.choice([1, 1, 1, -1]), user)
                    stats["votes"] += 1

        if random.random() < 0.45:
            for tag_name in random.sample(SAMPLE_TAGS, k=random.randint(1, 3)):
                tag, _ = Tag.objects.get_or_create(name=tag_name)
                Tagging.objects.get_or_create(
                    tag=tag, thread=thread, user=random.choice(users)
                )
                stats["tags"] += 1

        if random.random() < 0.35:
            Favorite.objects.get_or_create(thread=thread, user=demo)
            stats["favorites"] += 1
            if random.random() < 0.4:
                Favorite.objects.get_or_create(
                    thread=thread, user=random.choice(users)
                )
                stats["favorites"] += 1

        # Leave some threads unread for the demo user.
        if random.random() < 0.65:
            LastView.objects.update_or_create(
                thread=thread,
                user=demo,
                defaults={
                    "view_date": emails[-1].date - timedelta(hours=random.randint(1, 48))
                },
            )
            stats["last_views"] += 1

    return stats


def reset_lists(list_addrs: list[str]) -> None:
    with transaction.atomic():
        Thread.objects.filter(mailinglist__name__in=list_addrs).delete()
        Email.objects.filter(mailinglist__name__in=list_addrs).delete()
        MailingList.objects.filter(name__in=list_addrs).delete()


def finalize_lists(list_addrs: list[str]) -> None:
    for list_addr in list_addrs:
        for thread in Thread.objects.filter(mailinglist__name=list_addr):
            compute_thread_order_and_depth(thread)
        call_command("hyperkitty_warm_up_cache", list_addr, verbosity=0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--domain",
        default=os.environ.get("MAILMAN_DOMAIN", "lists.example.com"),
    )
    parser.add_argument(
        "--lists",
        default=os.environ.get(
            "SEED_LISTS",
            "delegates,paper-reviews,general,dev,announce,cpp,boost,test,"
            "committee,idle",
        ),
        help="Comma-separated local parts (without @domain)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=int(os.environ.get("SEED_THREADS", "12")),
    )
    parser.add_argument(
        "--replies",
        type=int,
        default=int(os.environ.get("SEED_REPLIES", "5")),
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing seeded lists/threads before inserting",
    )
    args = parser.parse_args()

    list_names = [f"{part.strip()}@{args.domain}" for part in args.lists.split(",")]

    Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={"domain": args.domain, "name": args.domain},
    )

    users = ensure_users()
    settings.HYPERKITTY_BATCH_MODE = True

    if args.reset:
        print(f"Resetting {len(list_names)} lists...")
        reset_lists(list_names)

    total_created = 0
    total_skipped = 0
    total_enrich = {"votes": 0, "tags": 0, "favorites": 0, "last_views": 0}
    for list_addr in list_names:
        local_part = list_local_part(list_addr)
        if local_part in INACTIVE_LIST_PARTS:
            print(f"Seeding {list_addr} (inactive — no messages)...")
            ensure_inactive_list(list_addr)
            created, skipped = 0, 0
        else:
            print(
                f"Seeding {list_addr} ({args.threads} threads x "
                f"{args.replies} messages)..."
            )
            created, skipped = seed_list(list_addr, args.threads, args.replies)
            if local_part in PRIVATE_LIST_PARTS:
                mark_list_private(list_addr, users)
        total_created += created
        total_skipped += skipped
        print(f"  +{created} messages ({skipped} skipped as duplicates)")
        enrich = enrich_discussions(list_addr, users)
        for key, value in enrich.items():
            total_enrich[key] += value
        print(
            f"  +{enrich['votes']} votes, {enrich['tags']} tags, "
            f"{enrich['favorites']} favorites, {enrich['last_views']} last-views"
        )

    linked = link_senders()
    print(f"Linked {linked} senders to Mailman participant ids")

    print("Computing thread structure and warming caches...")
    finalize_lists(list_names)

    demo_posts = Email.objects.filter(sender__address=DEMO_EMAIL).count()
    print(
        f"Done: {total_created} messages across {len(list_names)} lists "
        f"({total_enrich['votes']} votes, {total_enrich['tags']} tags, "
        f"{total_enrich['favorites']} favorites, "
        f"{total_enrich['last_views']} last-views)."
    )
    demo_sender = Sender.objects.filter(address=DEMO_EMAIL).first()
    print(f"Demo login: {DEMO_USERNAME} / {DEMO_PASSWORD} ({demo_posts} posts as participant)")
    if demo_sender and demo_sender.mailman_id:
        print(f"Demo mailman_id: {demo_sender.mailman_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
