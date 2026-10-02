"""WP-37: build the Felt board in Plane (run inside plane-api's manage.py shell).

One project, one waterfall: states left -> right are the flow, tickets are
created in tickets.TICKETS order so Plane's sort_order keeps that order.
Refuses to run twice (project FELT exists -> stop).
"""

import html
import sys

sys.path.insert(0, "/tmp")
from plane.app.serializers import ProjectSerializer
from plane.db.models import (
    Issue,
    IssueLabel,
    IssueRelation,
    Label,
    Profile,
    Project,
    ProjectMember,
    ProjectUserProperty,
    State,
    User,
    Workspace,
    WorkspaceMember,
)
from tickets import TICKETS

u = User.objects.get(email="lealmariop@gmail.com")
u.first_name, u.last_name, u.display_name = "Mario", "Leal", "Mario"
u.save()
ws, _ = Workspace.objects.get_or_create(
    slug="clockmost", defaults={"name": "clockmost", "owner": u}
)
WorkspaceMember.objects.get_or_create(workspace=ws, member=u, defaults={"role": 20})
p = Profile.objects.get(user=u)  # skip Plane's onboarding screens
p.is_onboarded = p.is_tour_completed = True
p.last_workspace_id = ws.id
p.onboarding_step = {
    "profile_complete": True,
    "workspace_create": True,
    "workspace_invite": True,
    "workspace_join": True,
}
p.save()
assert not Project.objects.filter(workspace=ws, identifier="FELT").exists(), (
    "board already built"
)

ser = ProjectSerializer(
    data={
        "name": "Felt",
        "identifier": "FELT",
        "network": 2,
        "description": "Felt work packages, one waterfall (WP-37). Specs live in the Felt repo.",
    },
    context={"workspace_id": ws.id},
)
ser.is_valid(raise_exception=True)
ser.save(created_by=u)
proj = ser.instance
ProjectMember.objects.create(project=proj, member=u, role=20, created_by=u)
ProjectUserProperty.objects.create(  # open as the board: columns = states, in board order
    project=proj,
    user=u,
    workspace=ws,
    display_filters={
        "layout": "kanban",
        "calendar": {"layout": "month", "show_weekends": False},
        "group_by": "state",
        "order_by": "sort_order",
        "sub_issue": True,
        "sub_group_by": None,
        "show_empty_groups": True,
    },
)

STATES = [  # name, group, colour
    ("Polish pile", "backlog", "#B49CDB"),
    ("Backlog", "backlog", "#A3A3A3"),
    ("Parked", "backlog", "#6E7781"),
    ("Ready", "unstarted", "#3F76FF"),
    ("In progress", "started", "#F59E0B"),
    ("Needs review", "started", "#E85D9E"),
    ("Done", "completed", "#16A34A"),
    ("Dropped", "cancelled", "#DC2626"),
]
states = {}
for i, (name, group, color) in enumerate(STATES):
    states[name] = State.objects.create(
        name=name,
        group=group,
        color=color,
        project=proj,
        workspace=ws,
        sequence=(i + 1) * 15000,
        default=(name == "Backlog"),
        created_by=u,
    )

LABELS = {
    "wp": "#3F76FF",
    "polish": "#B49CDB",
    "server": "#0EA5E9",
    "mario": "#F97316",
    "idea": "#A3A3A3",
    # metrics.py counts these; agent-ok marks work agents may take (WP-52)
    "failed-live": "#DC2626",
    "follow-up": "#F59E0B",
    "agent-ok": "#16A34A",
}
labels = {
    n: Label.objects.create(name=n, color=c, project=proj, workspace=ws, created_by=u)
    for n, c in LABELS.items()
}


def esc(s):
    return html.escape(s, quote=False)


def body(t):
    parts = [f"<p><strong>What:</strong> {esc(t['what'])}</p>"]
    if t.get("why"):
        parts.append(f"<p><strong>Why:</strong> {esc(t['why'])}</p>")
    if t.get("where"):
        parts.append(f"<p><strong>Where:</strong> {esc(t['where'])}</p>")
    if t["accept"]:
        items = "".join(
            f'<li data-type="taskItem" data-checked="false"><p>{esc(a)}</p></li>'
            for a in t["accept"]
        )
        parts.append(
            f'<p><strong>Accept:</strong></p><ul data-type="taskList">{items}</ul>'
        )
    parts.append(
        f"<p><strong>Depends:</strong> {esc(', '.join(t['depends']) or 'none')}</p>"
    )
    if t.get("evidence"):
        parts.append(f"<p><strong>Evidence:</strong> {esc(t['evidence'])}</p>")
    parts.append(
        f'<p><strong>Spec:</strong> <a href="{t["spec"]}">{esc(t["spec"].rsplit("/", 1)[-1])}</a></p>'
    )
    return "".join(parts)


issues = {}
for t in TICKETS:
    name = (
        t["title"]
        if t["key"].startswith(("POL-", "IDEA-"))
        else f"{t['key']} {t['title']}"
    )
    iss = Issue.objects.create(
        name=name[:255],
        description_html=body(t),
        state=states[t["state"]],
        project=proj,
        workspace=ws,
        priority="none",
        created_by=u,
    )
    for ln in t["labels"]:
        IssueLabel.objects.create(
            issue=iss, label=labels[ln], project=proj, workspace=ws, created_by=u
        )
    issues[t["key"]] = iss

rels = 0
for t in TICKETS:
    for d in t["depends"]:
        IssueRelation.objects.create(
            issue=issues[t["key"]],
            related_issue=issues[d],
            relation_type="blocked_by",
            project=proj,
            workspace=ws,
            created_by=u,
        )
        rels += 1

print(
    f"built FELT: {len(issues)} tickets, {len(states)} states, {len(labels)} labels, {rels} dependencies"
)
