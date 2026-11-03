"""Who receives a draft email, in which language, and why. Plain, exact code: no LLM here.

The LLM only writes the text (email_drafts.py). Who gets it is decided here, so it can be tested:
- chase_supplier  -> the supplier's contact person, in the supplier's language
- escalate        -> the project manager of the project
- a supplier with contact_policy "Via project manager" is NEVER written to directly: the draft goes
  to the project manager instead (asking them to contact the supplier)
- wait, book_in, none -> no email

Nothing here sends an email.
"""

INTERNAL_LANGUAGE = "Dutch"  # language for emails to colleagues; the brief names none, change it here
HEAD_OF_PURCHASING = "Head of Purchasing and Logistics"  # gets the escalations of projects without a project manager
VIA_PROJECT_MANAGER = "Via project manager"

REMINDER_TO_SUPPLIER = "reminder_to_supplier"
ESCALATION_TO_PM = "escalation_to_pm"
PM_CONTACTS_SUPPLIER = "pm_contact_supplier"

NEEDS_DRAFT = ["chase_supplier", "escalate"]


def _internal_contact(project: str, projects: dict[str, dict], employees: dict[str, dict]) -> tuple[str, dict, str | None]:
    """The project manager of the project; for a project without one (STOCK) the head of purchasing."""
    manager_id = projects[project]["project_manager_id"]
    if manager_id:
        return "project_manager", employees[manager_id], None
    head = next(e for e in employees.values() if e["role"] == HEAD_OF_PURCHASING)
    return "head_of_purchasing", head, f"Project {project} has no project manager: this goes to the {HEAD_OF_PURCHASING}."


def find_recipient(order: dict, action: str, suppliers: dict[str, dict], projects: dict[str, dict],
                   employees: dict[str, dict]) -> dict | None:
    """suppliers by supplier_id, projects by project, employees by employee_id.
    Returns None when the action needs no email. An unknown supplier or project raises KeyError."""
    if action not in NEEDS_DRAFT:
        return None
    supplier = suppliers[order["supplier_id"]]
    if action == "chase_supplier" and supplier["contact_policy"] != VIA_PROJECT_MANAGER:
        return {"kind": "supplier", "purpose": REMINDER_TO_SUPPLIER, "name": supplier["contact_person"],
                "email": supplier["email"], "language": supplier["language"], "note": None}
    kind, person, fallback_note = _internal_contact(order["project"], projects, employees)
    if action == "chase_supplier":
        purpose = PM_CONTACTS_SUPPLIER
        note = f"{supplier['name']} is '{VIA_PROJECT_MANAGER}': buyers never email this supplier directly."
    else:
        purpose, note = ESCALATION_TO_PM, None
    if fallback_note:
        note = f"{note} {fallback_note}" if note else fallback_note
    return {"kind": kind, "purpose": purpose, "name": person["name"], "email": person["email"],
            "language": INTERNAL_LANGUAGE, "note": note}


def sender_name(order: dict, employees_by_initials: dict[str, dict]) -> str:
    """The buyer of the order signs the email."""
    return employees_by_initials[order["buyer"]]["name"]
