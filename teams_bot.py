from botbuilder.core import TurnContext
from botbuilder.schema import HeroCard, CardAction, ActionTypes, Activity, ActivityTypes, Attachment
from rag import ask_policy_question

async def on_message_activity(turn_context: TurnContext):
    user_text = turn_context.activity.text

    if not user_text:
        return

    await turn_context.send_activity(
        Activity(type=ActivityTypes.typing)
    )

    answer = ask_policy_question(user_text)
    await turn_context.send_activity(answer)

async def send_suggested_questions(turn_context: TurnContext):

    card = HeroCard(
        title="📘 Caizin Policy Assistant",
        text="Please select a policy topic:",
        buttons=[
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