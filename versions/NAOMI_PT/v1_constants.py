from prompts import NAOMI_PT_PROMPT

V1_SYSTEM_PROMPT_TEXT = NAOMI_PT_PROMPT

BEGIN_OF_TEXT_TOKEN = "<|begin_of_text|>"
END_OF_TEXT_TOKEN = "<|end_of_text|>"
HEADER_START_TOKEN = "<|start_header_id|>"
HEADER_END_TOKEN = "<|end_header_id|>"
END_OF_TURN_TOKEN = "<|eot_id|>"

USER_HEADER = f"{HEADER_START_TOKEN}user{HEADER_END_TOKEN}"
ASSISTANT_HEADER = f"{HEADER_START_TOKEN}assistant{HEADER_END_TOKEN}"
SYSTEM_HEADER = f"{BEGIN_OF_TEXT_TOKEN}{HEADER_START_TOKEN}system{HEADER_END_TOKEN}"

SYSTEM_PROMPT_BLOCK = (
    f"{SYSTEM_HEADER}\n{V1_SYSTEM_PROMPT_TEXT}{END_OF_TURN_TOKEN}\n"
)

V1_FEWSHOT_PROMPT_PREFIX = f"""
{SYSTEM_PROMPT_BLOCK}
{USER_HEADER}
Here are a few examples of motivational interviewing counselor responses.

Example 1:
Task: Highlight the patient's motivations and relate them to their desire to improve their appearance.

Prior counselor utterance:
so you're really talking about, you know, making some changes in the you're eating and drinking. Why would you want to do some of those things?

Patient utterance:
Maybe to lose weight, make my appearance better.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
So again, bring your weight down a little bit.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Example 2:
Task: Validate the patient's concerns about their health and emphasize their awareness of the risks.

Prior counselor utterance:
So there's also some health things that you're a little concerned about.

Patient utterance:
And high blood pressure.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
You've heard quite a bit about these things.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Patient utterance:
Yes.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
so you're aware of what's going on with your family and want to be healthy as you get older.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Example 3:
Task: Recognize the patient's cautious approach to staying safe while encouraging them to engage in more outdoor activities.

Prior counselor utterance:
You know, you're being smart by keeping yourself safe. But you're kind of missing out on being outside and being active.

Patient utterance:
Yeah.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
and I don't know, you know, what would you like to focus on? You know, kind of, like, come up with an idea, maybe, to work on when you leave here. If you just had to kind of, like, pick something small to really focus on?
{END_OF_TURN_TOKEN}
{USER_HEADER}
Patient utterance:
Probably cut down on the eating, like, snacks, probably. Because I snack a lot. I think it's because you get bored and then you get the munchies and then I think that's why I'm exercising more. Because, like, I don't mind exercising. I actually like exercising, but it's, like, hard to find stuff to do during summertime except for ride your bike and play with friends, which I don't do because I don't have friends around the house, so.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
Mm-hmm. So, you're kind of, you're stuck right now in the fact that you're home and you get bored at home because your friends aren't there.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Example 4:
Task: Encourage the patient to establish a plan to manage their snacking habits effectively.

Prior counselor utterance:
Yeah, fair enough. Thanks for letting me know what's best for you because that's what's going to do the most, you know, help for you. This isn't about me. Haha. Alright. So, really, kind of thinking about the whole idea of the munchies, if you had to have just a little bit of a plan with what you were going to do with that, what would that be?

Patient utterance:
Probably, like, snack only twice a day between each meal, because usually I just, like, snack just all day. So, I think that's what I could do to, like
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
Alright. so really kind of give yourself like, a, this is my between breakfast and lunch snack.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Example 5:
Task: Discuss the patient's main motivation for losing weight and tie it to their aspirations for their important event.

Prior counselor utterance:
Well, what is the, the most important reason that you'd want to do lose weight?

Patient utterance:
To get healthier so that I won't be unhealthy and then I can be good for my senior year.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
So, you're really thinking about senior year, maybe some prom.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Example 6:
Task: Validate the patient's anticipation for their senior year and inquire about potential obstacles they may encounter.

Prior counselor utterance:
So you really have this idea that you're looking forward to senior year. You want to be healthy and cutting back on the snacking.

Patient utterance:
Yeah.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
What are some things that could get in the way?
{END_OF_TURN_TOKEN}
{USER_HEADER}
Patient utterance:
If my sister moves back in and brings her snacks with her.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
Okay, because they'll be around. Little reminders.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Example 7:
Task: Empathize with the patient's feelings about controlling their diet and acknowledge their autonomy in decision-making.

Prior counselor utterance:
It isn't fun to have somebody tell you what to eat at all.

Patient utterance:
Yeah I don't like doing that.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
So you feel a little bit more in control now because you're the one who is deciding what you're going to have for snack.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Example 8:
Task: Encourage the patient to take the first step towards achieving their goal of reducing snack intake.

Prior counselor utterance:
Good. You've got a good, good family. You're a good member of the family and so they want to be good to you, too. Alright, well, I mean, what's the first thing that you could do in order to, to reach your goal of, you know, cutting back to maybe two snacks a day?

Patient utterance:
Go grocery shopping.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
Yeah. Grocery shopping. For healthy stuff only.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Example 9:
Prior counselor utterance:
So what kinds of things in the house would be a good option?

Patient utterance:
Maybe flavored water. Gatorade. Crystal Light. And maybe stuff like is healthy?
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
so you're really thinking like a wide sale, like how do you tell what types of drinks have calories in them or not.
{END_OF_TURN_TOKEN}
{USER_HEADER}
Patient utterance:
Yes.
{END_OF_TURN_TOKEN}
{ASSISTANT_HEADER}
So you're absolutely right, you get all the info that you need about the stuff that you're drinking and eating from the food labels.
{END_OF_TURN_TOKEN}
{USER_HEADER}
"""