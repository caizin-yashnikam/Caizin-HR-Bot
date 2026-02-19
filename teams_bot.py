from botbuilder.core import TurnContext
from botbuilder.schema import HeroCard, CardAction, ActionTypes, Activity, ActivityTypes, Attachment
from fastapi import logger
import logging
from rag import ask_policy_question



logger = logging.getLogger(__name__)


# =========================
# EMAIL RESOLUTION
#
# Teams work accounts set from_property.name to the user's UPN which
# is usually their work email (user@company.com).
# If your org uses a different format, swap this logic for a Graph API
# call: GET https://graph.microsoft.com/v1.0/users/{aadObjectId}/mail
# =========================
def _get_employee_email(turn_context: TurnContext) -> str:
    """Extract the employee's email from the Teams activity."""
    from_prop = turn_context.activity.from_property

    if not from_prop:
        logger.warning("[email] from_property is None")
        return ""


    logger.info(f"[email] from_prop.id:   {from_prop.id}")
    logger.info(f"[email] from_prop.name: {from_prop.name}")
    logger.info(f"[email] aad_object_id:  {getattr(from_prop, 'aad_object_id', None)}")

     # Also log channel_data for extra info
    channel_data = turn_context.activity.channel_data or {}
    logger.info(f"[email] channel_data: {channel_data}")


    # Option 1: name field contains UPN / email (most common for work accounts)
    name = from_prop.name or ""
    if "@" in name:
        logger.info(f"[email] ✅ found in name: {name}")
        return name.lower().strip()

    # Option 2: id field sometimes contains the email in webchat / dev testing
    user_id = from_prop.id or ""
    if "@" in user_id:
        logger.info(f"[email] ✅ found in id: {user_id}")
        return user_id.lower().strip()

      # Option 3: Construct email from display name as firstname.lastname@caizin.com
    if name:
        parts = name.lower().split()
        email = f"{parts[0]}.{parts[-1]}@caizin.com" if len(parts) >= 2 else f"{parts[0]}@caizin.com"
        logger.info(f"[email] ✅ constructed from name: {email}")
        return email

    logger.warning("[email] could not resolve email")

    return ""


# =========================
# MESSAGE HANDLER  (updated: passes employee_email)
# =========================
async def on_message_activity(turn_context: TurnContext):
    user_text = turn_context.activity.text

    if not user_text:
        return

    await turn_context.send_activity(
        Activity(type=ActivityTypes.typing)
    )

    employee_email = _get_employee_email(turn_context)
    logger.info(f"[bot] question='{user_text}' | email='{employee_email}'")

    answer = ask_policy_question(user_text, employee_email=employee_email)
    await turn_context.send_activity(answer)


# =========================
# WELCOME CARD  (updated: added Leave Balance button)
# =========================
async def send_suggested_questions(turn_context: TurnContext):

    card = HeroCard(
        title="📘 Caizin Policy Assistant",
        text="Please select a policy topic:",
        buttons=[
            CardAction(
                type=ActionTypes.im_back,
                title="My Leave Balance",
                value="What is my leave balance?"
            ),
            CardAction(
                type=ActionTypes.im_back,
                title="Leaves",
                value="Tell me about leave policy"
            ),
            CardAction(
                type=ActionTypes.im_back,
                title="Fitness Policy",
                value="Tell me about fitness reimbursement policy"
            ),
            CardAction(
                type=ActionTypes.im_back,
                title="Travel Policy",
                value="Tell me about travel policy"
            ),
            CardAction(
                type=ActionTypes.im_back,
                title="Referral Policy",
                value="Tell me about referral policy"
            ),
            CardAction(
                type=ActionTypes.im_back,
                title="POSH Policy",
                value="Tell me about POSH policy"
            ),
        ]
    )

    attachment = Attachment(
        content_type="application/vnd.microsoft.card.hero",
        content=card
    )

    reply = Activity(
        type="message",
        attachments=[attachment]
    )

    await turn_context.send_activity(reply)
