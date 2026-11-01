# Client: Brakwater Boats B.V.
Shipyard (45 people) building aluminium workboats, harbour service boats and patrol RIBs.
Contact: Mark Dekker, Head of Purchasing and Logistics. Buyers: Linda Verhoeven (LV) and
Youssef Amrani (YA). Project managers: Sanne de Wit and Joris Bakker.

## Problem
The purchasing team spends too much time tracking open purchase orders and following up with
suppliers. Every now and then something slips through, with consequences for the delivery of a boat.
Today Linda runs export_open_orders.py every Monday and works through the CSV by hand, reads the
memos in the ERP and writes reminder emails to suppliers one by one. This takes hours every week.

## What Mark needs
1. Grip on open orders: without digging, see which orders are late, which suppliers have not
   confirmed an order, and which deliveries are coming up soon.
2. Less manual follow-up: draft the reminder emails, in the supplier's language.
3. Control stays with his team: help, not a black box. Buyers own the supplier relationships.
   Nothing is sent and nothing is changed in the ERP without a buyer's approval.
4. Something that works soon: a small first version the team can use next month. Mark wants to
   understand what it does, what it saves and what the risks are.

## What we know
- About 90% of follow-ups are routine. About 10% show a real problem (a delay, no answer, a price
  change) that must be escalated to the project manager because it can affect a boat delivery.
- Supplier answers are written by the buyers in the ERP memo (Dutch, German, English). There is no
  email inbox in this version.
- Some suppliers have contact_policy "Via project manager": never email them directly.
- When a memo shows a change (new delivery date, confirmation received), the ERP should be updated.
  The API is read only, so the system PROPOSES the update and a buyer approves it.
- Escalation emails are always reviewed by a human before they go out.
- No supplier or open order may be forgotten.
- The data is fictional, so no GDPR issue for this case.
- The 60 open orders in the ERP sandbox are our evaluation set.

## Success for version 1
A simple page where a buyer sees every open order grouped by urgency, with a suggested action
(chase, wait, escalate, book in, none), a one-line reason, a draft email where needed and a
proposed ERP update, and can Approve or Reject each one.
