# List of all 24 therapist MI codes from original excel sheet merged. 
ORIGINAL_HCP_CODES = [
    "GINFO+", "GINFO-", "EA", "AF", "SPT", "RCHT+", "RCHT-", "RCML+", "RCML-",
    "RO", "RAMB", "AR", "RBA", "SUM", "QECHT+", "QECHT-", "QECML+", "QECML-",
    "QEB", "QEF", "ADV-", "ADV+", "RC", "CON"
]

# SUM, AR, RO, and all MIIN codes have been removed as they are not selectable.

HCP_CODES = [
    "GINFO+", "EA", "AF", "SPT", "RCHT+", "RCHT-", "RCML+", "RCML-",
    "RAMB", "RBA", "QECHT+", "QECHT-", "QECML+", "QECML-",
    "QEB", "QEF", "ADV+"
]


# List of all 7 patient MI codes 
USR_CODES = [
    "HUPW",   # High Unspecific Patient Willingness
    "PSO",    # Patient Statement of Outcome
    "CML+",   # Change Talk - Positive
    "CML-",   # Change Talk - Negative
    "CHT+",   # Commitment Talk - Positive
    "CHT-",   # Commitment Talk - Negative
    "AMB"     # Ambivalence
]





#### RELATING TO MI QUALITY ### 
# MI-inconsistent (MIIN) therapist behaviors to penalize in scoring
MIIN_CODES = ["RC", "CON", "ADV-", "GINFO-"]


# Stage-specific codes that should NOT be selected.
STAGE_SPECIFIC_BLOCKLIST = {
    "ENGAGING": ["SPT", "GINFO+", "ADV+", "QECML+", "QECML-"],
    "FOCUSING": [], # No specific codes to block beyond MIIN
    "EVOKING": ["QEB", "RBA"],
    "PLANNING": []
}

# Additive score bonuses for codes that are particularly encouraged in a stage.
# These values are scaled down to act as a "nudge" rather than a "shove".
STAGE_CODE_BOOSTS = {
    "ENGAGING": {
        "RCHT+": 0.015,
        "QECHT+": 0.01
    },
    "FOCUSING": {
        "RCHT+": 0.015
    },
    "EVOKING": {
        "RCHT+": 0.02,   # Strong preference
        "QECHT+": 0.015
    },
    "PLANNING": {
        "RCML+": 0.02,   # "especially"
        "RCHT+": 0.02,   # "especially"
        "QECML+": 0.015,
        "QEB": 0.015,
        "AF": 0.015,     # "especially"
        "GINFO+": 0.01,  # "acceptable"
        "ADV+": 0.01     # "acceptable"
    }
}



# 4 Phases of the MI Session
STAGE_NAMES = ["ENGAGING", "FOCUSING", "EVOKING", "PLANNING"]

# Intro message for new sessions
INTRO_MSG = "Hello! My name is NAOMI and I am a virtual counselor..."



# Which MI codes belong to what behavior group
# The final, corrected mapping of codes to their statistical groups.
CODE_TO_GROUP = {
    # REFLECTION Group (RBA is now included)
    "RCHT+": "REFLECTION", "RCHT-": "REFLECTION",
    "RCML+": "REFLECTION", "RCML-": "REFLECTION",
    "RAMB": "REFLECTION", "RBA": "REFLECTION",
    "RO": "REFLECTION",

    # QUESTION Group
    "QECHT+": "QUESTION", "QECHT-": "QUESTION",
    "QECML+": "QUESTION", "QECML-": "QUESTION",
    "QEB": "QUESTION", "QEF": "QUESTION",

    # AFFIRMATION Group
    "AF": "AFFIRMATION", "EA": "AFFIRMATION",

    # SUPPORT Group
    "SPT": "SUPPORT",

    # INFO Group
    "GINFO+": "INFO", "ADV+": "INFO"
}

STAGE_DISTRIBUTIONS = {
    "ENGAGING": {
        # Based on PDF: R(50) + Q(20) + A/EA(10) = 80% of selectable codes
        "REFLECTION": 0.625,  # 50 / 80
        "QUESTION":   0.250,  # 20 / 80
        "AFFIRMATION":0.125,  # 10 / 80
        "SUPPORT":    0.000,
        "INFO":       0.000
    },
    "FOCUSING": {
        # Based on PDF: R(40) + Q(20) + A/EA/S(10) + I(20) = 90%
        # The 10% for A/EA/S is split between AFFIRMATION and SUPPORT.
        "REFLECTION": 0.444,  # 40 / 90
        "QUESTION":   0.222,  # 20 / 90
        "AFFIRMATION":0.056,  # 5 / 90
        "SUPPORT":    0.056,  # 5 / 90
        "INFO":       0.222   # 20 / 90
    },
    "EVOKING": {
        # Based on PDF: R(50) + Q(10) + A/EA(10) + S(10) + I(10) = 90%
        "REFLECTION": 0.556,  # 50 / 90
        "QUESTION":   0.111,  # 10 / 90
        "AFFIRMATION":0.111,  # 10 / 90
        "SUPPORT":    0.111,  # 10 / 90
        "INFO":       0.111   # 10 / 90
    },
    "PLANNING": {
        # Based on PDF: R(25) + Q(12.5) + A/EA(12.5) + S(12.5) + I(25) = 87.5%
        "REFLECTION": 0.286,  # 25 / 87.5
        "QUESTION":   0.143,  # 12.5 / 87.5
        "AFFIRMATION":0.143,  # 12.5 / 87.5
        "SUPPORT":    0.143,  # 12.5 / 87.5
        "INFO":       0.285   # 25 / 87.5
    }
}


STAGE_CHAINS = {
        "ENGAGING": [
            ([("C", "CHT+"), ("T", "RCHT+"), ("C", "*")], "QECHT+"),
            ([("C", "CHT-"), ("T", "RCHT-"), ("C", "*")], "QECHT-"),
            ([("C", "CML+"), ("T", "RCML+"), ("C", "*")], "AF"),
            ([("C", "CML-"), ("T", "RBA"),   ("C", "*")], "QECML-"),
            ([("C", "AMB"),  ("T", "RAMB"),  ("C", "*")], "QECHT+"),
            ([("C", "HUPW")], "EA"),
            ([("C", "PSO"),  ("T", "RO"),    ("C", "*")], "QECHT+"),
        ],
         "FOCUSING": [
            ([("C", "CHT+"), ("T", "RCHT+"), ("C", "*")], "QECHT+"),
            ([("C", "CHT-"), ("T", "RCHT-"), ("C", "*")], "QECHT-"),
            ([("C", "CML+"), ("T", "RCML+"), ("C", "*")], "AF"),
            ([("C", "CML-"), ("T", "RBA"),   ("C", "*")], "QECML-"),
            ([("C", "AMB"),  ("T", "RAMB"),  ("C", "*")], "QECHT+"),
            ([("C", "HUPW")], "EA"),  # Direct match
            ([("C", "PSO"),  ("T", "RO"),    ("C", "*")], "QECHT+"),

            ([("T", "ADV+"),   ("C", "*")], "QEF"),
            ([("T", "GINFO+"), ("C", "*")], "QEF"),
        ],
        "EVOKING": [
            # Client Change Talk triggers
            ([("C", "CHT+"), ("T", "RCHT+"), ("C", "*")], "QECML+"),
            ([("C", "CHT-"), ("T", "RCHT-"), ("C", "*")], "QECHT+"),
            ([("C", "CML+"), ("T", "RCML+"), ("C", "*")], "AF"),
            ([("C", "CML-"), ("T", "AR"),     ("C", "*")], "SPT"),
            ([("C", "AMB"),  ("T", "RAMB"),   ("C", "*")], "QECHT+"),
            ([("C", "HUPW"), ("T", "EA"),     ("C", "*")], "QECHT+"),
            ([("C", "PSO"),  ("T", "RO"),     ("C", "*")], "QECHT+"),

            # Therapist-only triggers (with client wildcard in between)
            ([("T", "ADV+"),   ("C", "*")], "QEF"),
            ([("T", "GINFO+"), ("C", "*")], "QEF"),
        ],
        "PLANNING": [
            # CHT+ -> RCHT+ -> * -> OQECML+
            ([("C", "CHT+"), ("T", "RCHT+"), ("C", "*")], "QECML+"),

            # CHT- -> RCHT- -> * -> QECHT-
            ([("C", "CHT-"), ("T", "RCHT-"), ("C", "*")], "QECHT-"),

            # CML+ -> RCML+ -> * -> AF
            ([("C", "CML+"), ("T", "RCML+"), ("C", "*")], "AF"),

            # CML- -> QEB- -> * -> ADV+
            ([("C", "CML-"), ("T", "QEB-"),  ("C", "*")], "ADV+"),

            # AMB -> RAMB -> * -> QECHT+
            ([("C", "AMB"),  ("T", "RAMB"),  ("C", "*")], "QECHT+"),

            # HUPW -> AF -> * -> QECML+
            ([("C", "HUPW"), ("T", "AF"),    ("C", "*")], "QECML+"),

            # PSO -> RO -> * -> QECML+
            ([("C", "PSO"),  ("T", "RO"),    ("C", "*")], "QECML+"),

            # Therapist-only
            ([("T", "ADV+"),   ("C", "*")], "QEF"),
            ([("T", "GINFO+"), ("C", "*")], "QEF"),
        ]
    }

FOCUSING_INTRO_Q = "[QECML+] Which behavior would you like to start with? We could start with diet, physical activity, or another part of your lifestyle that you'd like to change."

EVOKING_INTRO_Q = "[QECML+] Why do you want to start here?"

PLANNING_INTRO_Q = "[QECML+] What are some steps you would consider taking to help you achieve your goal? What actions seem within reach this time? "


# --------------------- MI Code Definitions Per Stage --------------------- #
MI_CODE_DEFS = {
    "ENGAGING": {
        "RCHT+": "reflective statements that restate or rephrase your client's language expressing desire, ability, reasons, or need to change their weight-related behavior.",
        "RCHT-": "reflective statements that restate or rephrase your client's language expressing desire, ability, reasons, or need not change their weight-related behavior.",
        "RCML+": "reflective statements that restate or rephrase your client's language expressing their intentions, plans, or any specific, concrete actions your client has made to change their weight-related behavior, even tentative ones.",
        "RCML-": "reflective statements that restate or rephrase your client's language expressing their reluctance to set an intention or plan to change their weight-related behavior, or any specific, concrete steps taken to avoid changing their weight-related behavior.",
        "RAMB":  "reflective statements that restate or rephrase your client's language expressing their mixed or conflicting feelings about changing their weight-related behavior. Reflections of ambivalence should start with the reflection of change talk negative [RCHT-] and end with the reflection of change talk positive [RCHT+].",
        "RBA":   "reflective statements that restate or rephrase barriers identified by your client that could get in the way of enacting the specific, concrete action steps that are part of their behavior change plan.",
        "QECHT+": "Ask a question that encourages the client to share their desire, ability, reasons for, or need to change their weight-related behavior.",
        "QECHT-": "Ask a question that invites the client to discuss their hesitations or their desire, ability, reasons against, or need not to change their weight-related behavior.",
        "QECML-": "Ask a question that explores your client's doubts about or reluctance to change, or explicit intentions, plans, or any actions the client has made to avoid changing their weight-related behavior.",
        "EA":     "Emphasize your client's decision-making autonomy, right to choose the direction and course of treatment, and express themselves freely.",
        "AF":     "Express appreciation for the client's thoughts, hopes, feelings, experiences or their efforts to change their behavior to reinforce and build confidence.",
    },
    "FOCUSING": {
        "RCHT+": "reflective statements that restate or rephrase your client's language expressing desire, ability, reasons, or need to change a specific aspect of their weight-related behavior.",
        "RCHT-": "reflective statements that restate or rephrase your client's language expressing desire, ability, reasons, or need not change a specific aspect of their weight-related behavior.",
        "RCML+": "reflective statements that restate or rephrase your client's language expressing their intentions, plans, or any specific, concrete actions your client has made to change a specific aspect of their weight-related behavior, even tentative ones.",
        "RCML-": "reflective statements that restate or rephrase your client's language expressing their reluctance to set an intention or plan to change a specific aspect of their weight-related behavior, or any specific, concrete steps to avoid changing a specific aspect of their weight-related behavior.",
        "RAMB":  "reflective statements that restate or rephrase your client's language expressing their mixed or conflicting feelings about changing a specific aspect of their weight-related behavior. Reflections of ambivalence should start with the reflection of change talk negative [RCHT-] and end with the reflection of change talk positive [RCHT+].",
        "RBA":   "reflective statements that restate or rephrase barriers identified by your client that could get in the way of enacting the specific, concrete action steps that are part of their behavior change plan.",
        "QECHT+": "Ask a question that encourages the client to share their desire, ability, reasons for, or need to change a specific aspect of their weight-related behavior.",
        "QECHT-": "Ask a question that invites the client to discuss their hesitations or their desire, ability, reasons against, or need not to change a specific aspect of their weight-related behavior.",
        "QECML+": "Ask a question that encourages the client to explore their intentions, plans, or any specific, concrete actions the client has already made towards changing a specific aspect of their weight-related behavior.",
        "QECML-": "Ask a question that explores your client's doubts about or reluctance to change, or explicit intentions, plans, or any specific, concrete actions the client has made to avoid changing a specific aspect of their weight-related behavior.",
        "GINFO+": "Provide factual information using neutral language, specifically to offer different options or choices for the client to consider as a focus, keeping the information brief and acknowledging your client's autonomy.",
        "ADV+":   "Offer advice or suggestions related to potential focus areas for weight loss, using neutral language, keeping the advice brief and acknowledging your client's autonomy.",
        "EA":     "Emphasize your client's decision-making autonomy, right to choose the direction and course of treatment, and express themselves freely.",
        "AF":     "Express appreciation for the client's thoughts, hopes, feelings, experiences or their efforts to change their behavior to reinforce and build confidence.",
        "SPT":    "Express understanding of your client's experience, thoughts, or feelings to build rapport.",
    },

    "EVOKING": {
        "RCHT+": "reflective statements that restate or rephrase your client's language expressing desire, ability, reasons, or need to change the target behavior.",
        "RCHT-": "reflective statements that restate or rephrase your client's language expressing desire, ability, reasons, or need not to change the target behavior.",
        "RCML+": "reflective statements that restate or rephrase your client's language expressing their intentions, plans, or specific, concrete actions your client has made to change the target behavior, even tentative ones.",
        "RCML-": "reflective statements that restate or rephrase your client's language expressing their reluctance to set an intention or plan to change the target behavior, or take specific, concrete steps taken to avoid changing the target behavior.",
        "RAMB":  "reflective statements that restate or rephrase your client's language expressing their mixed or conflicting feelings about changing the target behavior. Reflections of ambivalence should start with the reflection of change talk negative [RCHT-] and end with the reflection of change talk positive [RCHT+].",
        "RBA":   "reflective statements that restate or rephrase barriers identified by your client that could get in the way of enacting the specific, concrete action steps that are part of their behavior change plan.",
        "QECHT+": "Ask a question (both open and closed-ended questions are allowed, although open-ended questions are preferable) that encourages the client to share their desire, ability, reasons for, or need to change the target behavior.",
        "QECHT-": "Ask a question (both open and closed-ended questions are allowed, although open-ended questions are preferable) that invites the client to discuss their hesitations or their desire, ability, reasons against, or need not to change the target behavior.",
        "QECML+": "Ask a question (both open and closed-ended questions are allowed, although open-ended questions are preferable) that encourages the client to explore their intentions, plans, or any specific concrete actions they have already made towards changing the target behavior.",
        "QECML-": "Ask a question (both open and closed-ended questions are allowed, although open-ended questions are preferable) that explores your client's doubts about or reluctance to change, or explicit intentions, plans, or any specific, concrete actions the client has made to avoid changing the target behavior.",
        "EA":     "Emphasize your client's decision-making autonomy, right to choose the direction and course of treatment, and express themselves freely.",
        "AF":     "Express appreciation for the client's thoughts, hopes, feelings, experiences or their efforts to change their behavior to reinforce and build confidence.",
        "SPT":    "Offer statements that express understanding of their client's experience, thoughts, or feelings.",
        "GINFO+": "Provide factual information using neutral language, keeping the information provided brief, which means limited to a single idea or fact, and specifically acknowledge your client's autonomy in deciding if and how to use this information.",
        "ADV+":   "Offer advice or suggestions for weight loss using neutral language, keeping the advice provided brief, which means limited to a single idea or fact, and specifically acknowledge your client's autonomy in deciding if and how to use the advice.",
    },
    "PLANNING": {
        "RCHT+": "reflective statements that restate or rephrase your client's language expressing desire, ability, reasons, or need to take specific, concrete steps toward changing the target behavior.",
        "RCHT-": "reflective statements that restate or rephrase your client's language expressing desire, ability, reasons, or need not to take specific, concrete steps toward changing the target behavior.",
        "RCML+": "reflective statements that restate or rephrase your client's language expressing their intentions, plans, or specific, concrete steps taken to change the target behavior, even tentative ones.",
        "RCML-": "reflective statements that restate or rephrase your client's language expressing their reluctance to set an intention, plan, or take specific, concrete steps toward changing the target behavior.",
        "RAMB":  "reflective statements that restate or rephrase your client's language expressing their mixed or conflicting feelings about taking specific, concrete steps toward changing the target behavior. Reflections of ambivalence should start with the reflection of change talk negative [RCHT-] and end with the reflection of change talk positive [RCHT+].",
        "RBA":   "reflective statements that restate or rephrase barriers identified by your client that could get in the way of enacting the specific, concrete action steps that are part of their behavior change plan.",
        "QECHT+": "Ask a question (both open and closed-ended questions are allowed, although open-ended questions are preferable) that encourages the client to share their desire, ability, reasons for, or need to take specific, concrete steps toward changing the target behavior.",
        "QECHT-": "Ask a question (both open and closed-ended questions are allowed, although open-ended questions are preferable) that invites the client to discuss their hesitations or their desire, ability, reasons against, or need not to take specific, concrete steps toward changing the target behavior.",
        "QECML+": "Ask a question (both open and closed-ended questions are allowed, although open-ended questions are preferable) that encourages the client to explore their intentions, plans, and specific, concrete steps the client can or already has made towards changing the target behavior.",
        "QECML-": "Ask a question (both open and closed-ended questions are allowed, although open-ended questions are preferable) that explores your client's doubts about or reluctance to change, or explicit intentions, plans, or specific, concrete steps the client can or has made to avoid changing the target behavior.",
        "QEB":    "Ask a question (both open and closed-ended questions are allowed, although open-ended questions are preferable) about anticipated challenges and barriers that might stand in the way of or derail implementation of the behavior change plan or the specific action steps in this plan.",
        "GINFO+": "Provide factual information specifically to help with the planning process, using neutral language, keeping the information brief, and acknowledging your client's autonomy.",
        "ADV+":   "Offer advice or suggestions for specific action steps on the behavior change plan, in the context of helping the client build their plan, using neutral language, keeping the advice brief, and acknowledging your client's autonomy.",
        "EA":     "Emphasize the client's decision-making autonomy, right to choose the direction and course of treatment, and express themselves freely.",
        "AF":     "Express appreciation for the client's thoughts or efforts, especially by highlighting their personal strengths and ability, to reinforce self-efficacy for their behavior change plan and build confidence.",
        "SPT":    "Offer statements that express understanding of their client's experience, thoughts, or feelings to build rapport.",
        "SUM":    "provide a summary consolidating the previously discussed action steps into the behavior change plan, stating the overall goal of the behavior change plan steps along with any reasons why the goal and action steps were selected by your client and reinforcing the client's ownership of the behavior change plan.",
    }
}

ORDER = ["ENGAGING", "FOCUSING", "EVOKING", "PLANNING", "END"]

# ---- For stage transition ---- #
# Prolonged-stage override thresholds
MAX_TURNS = {
    "ENGAGING": 10,
    "FOCUSING": 8,
    "EVOKING": 12,
    "PLANNING": 12,
}

MAX_CHARS = {
    "ENGAGING": 6000,
    "FOCUSING": 5000,
    "EVOKING": 8000,
    "PLANNING": 8000,
}

# Minimum turns before we even start asking the LLM to evaluate
MIN_TURNS_BEFORE_LLM = {
    "ENGAGING": 6,
    "FOCUSING": 4,
    "EVOKING": 6,
    "PLANNING": 6,
}


# List of valid user IDs for V3.1 and V4. 
# emails will start with gXX for V3.1 and hXX for V4
# Generated using generate_ids.py
VALID_IDS = [
    'j4cnxrzp',
    'em5m4262',
    'y44p6wsp',
    '5man9kxg',
    'n5jpzhnc',
    'yzdnm8dd',
    'yuptky4b',
    'x7hrvvxk',
    '9eeo4nk7',

    'aqy8kxvx',
    'ebj64oom',
    'yndxo54x',
    'iyay9mow',
    '2c72ih8n',
    'omwijdpi',

    '253d2thc',
    'eyhu8sui',
    'i7mh45ni',
    'sdao5sqx',
    'k2jc6kj7',
    'b2ros8w3',
    'dqq3w5be',
    '77vxea76',
    'x2tcbavw',
    'fwsujxnt',
    '72vmfz6z',
    'mfpon6si',
    'uc4qct6p',
    'ukuxbhxv',
    'ud368fxd', # h21

    'ach92wbs',
    '7d5m69qy',
    'cfm7x58k',
    'uvkbspxa',
    'p5u9au92',
    '6q5adnso',
    'nwm8dung',
    '4wgcjfji',
    'dioqtu5t',
    'dvvt84dc',
    'test1',
    'test2',
    'test3',
    'test4'
]



OLD_VALID_IDS = ['testtest', '08TDWNlz', '1sanxBwI', '4z1rcrFo', '7N3FGhHt', '9Zp57DK7', 'F4BPUOZB', 'FxHJCQ2j', 'HOLmHuaT', 'Jo9pHcwx', 'Krx1XLqE', 'MXmZD5Av', 'OE2ftK9x', 'P1OgLwCP', 'Q8r2FCWQ', 'QgQoY5oN', 'QnS1Twp4', 'R6CXUT1b', 'RQH6dw0Z', 'S2V3yQpO', 'U759m48F', 'UQVsnt7J', 'WNjjwanG', 'YPUJZX8Q', 'b3z9Fbaw', 'bug6lpO6', 'cxHyJoOp', 'dWQzhB4k', 'e1YyK2Np', 'empyjrg2', 'f0eR5fiG', 'gMkMMIh6', 'hbUW83WJ', 'hl9vXSAL', 'hlKqU5ST', 'jOfyVfVy', 'l4Cxlyt6', 'mBbeWLBE', 'nhODS381', 'p586RQew', 'qTWbw8k1', 'raJVQMnc', 's5STyiTh', 'toezkLWs', 'uXeFcPoN', 'vKCP7EXX', 'vOpXtRVU', 'w8HGHQFR', 'x8HKI6my', 'xPCn08oi', 'zx78C4fQ']
