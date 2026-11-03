"""Hand-written practice questions for the demo books, so practice works without an AI key.

They have the shape the AI fills in (GeneratedQuestion) and pass the same program checks
(tests/unit/test_demo_questions.py). `python -m scripts.seed` stores them in the demo family's
question bank, filed under the exercise named next to each question (None = the chapter). The Class 7
set has enough short and long answers for a chapter test (sections C and D); marking written answers
needs the AI, the rest does not.

Each list is in the language of the child it is for: Aarav learns in Hinglish, Anaya in Hindi.
"""

from typing import Any

from app.core.enums import QuestionFormat, QuestionStyle
from app.question_generation.schemas import GeneratedQuestion

_EMPTY: dict[str, Any] = {
    "case": None,
    "options": [],
    "correct_option": None,
    "numeric_answer": None,
    "unit": None,
    "accepted_answers": [],
    "match_left": [],
    "match_right": [],
    "model_answer": None,
    "key_points": [],
    "source_tags": ["S1"],
}


def _q(fmt: QuestionFormat, style: QuestionStyle, difficulty: str, **fields: Any) -> GeneratedQuestion:
    return GeneratedQuestion.model_validate(
        {**_EMPTY, "format": fmt, "style": style, "difficulty": difficulty, **fields}
    )


MCQ, CASE, AR = QuestionFormat.MCQ, QuestionFormat.CASE_BASED, QuestionFormat.ASSERTION_REASON
SHORT, LONG = QuestionFormat.SHORT_ANSWER, QuestionFormat.LONG_ANSWER
PICTURE, COUNT, MATCH = QuestionFormat.VISUAL_CHOICE, QuestionFormat.COUNTING, QuestionFormat.MATCHING
RECALL, CONCEPT, APPLY, HOTS = (
    QuestionStyle.RECALL,
    QuestionStyle.CONCEPTUAL,
    QuestionStyle.APPLICATION,
    QuestionStyle.HOTS,
)

# Class 7 Mathematics, "Chapter 4 Simple Equations" (scripts/sample_data/class7-maths-sample.txt).
CLASS_7_MATHS: list[tuple[str | None, GeneratedQuestion]] = [
    (
        "4.1",
        _q(
            MCQ,
            RECALL,
            "easy",
            text="x + 5 = 12 mein x ki value kya hai?",
            options=["5", "7", "12", "17"],
            correct_option=1,
            hints=["x ke saath 5 juda hai. Use hatane ke liye kya karoge?"],
            concept="Jo number variable mein joda gaya hai, use dono taraf se ghatate hain.",
            steps=["Dono taraf se 5 ghatao: x + 5 - 5 = 12 - 5", "x = 7"],
            final_answer="x = 7",
        ),
    ),
    (
        "4.1",
        _q(
            MCQ,
            RECALL,
            "easy",
            text="y - 4 = 9 ho to y kitna hai?",
            options=["5", "13", "36", "94"],
            correct_option=1,
            hints=["y mein se 4 ghataya gaya hai. Dono taraf 4 jodo."],
            concept="Jo number ghataya gaya hai, use dono taraf jodte hain.",
            steps=["Dono taraf 4 jodo: y - 4 + 4 = 9 + 4", "y = 13"],
            final_answer="y = 13",
        ),
    ),
    (
        "4.1",
        _q(
            MCQ,
            RECALL,
            "easy",
            text="3p = 18 ho to p kitna hai?",
            options=["3", "6", "15", "54"],
            correct_option=1,
            hints=["p ko 3 se guna kiya gaya hai. Dono taraf 3 se bhaag do."],
            concept="Variable ko kisi number se guna kiya ho to dono taraf usi number se bhaag dete hain.",
            steps=["Dono taraf 3 se bhaag do: 3p ÷ 3 = 18 ÷ 3", "p = 6"],
            final_answer="p = 6",
        ),
    ),
    (
        "4.1",
        _q(
            MCQ,
            CONCEPT,
            "medium",
            text="m / 4 = 2 solve karne ke liye dono taraf kya karenge?",
            options=["4 ghatayenge", "4 se bhaag denge", "4 se guna karenge", "2 jodenge"],
            correct_option=2,
            hints=["m ko 4 se bhaag diya gaya hai. Bhaag ka ulta kya hai?"],
            concept="Bhaag ko hatane ke liye dono taraf usi number se guna karte hain.",
            steps=["Dono taraf 4 se guna karo: (m / 4) × 4 = 2 × 4", "m = 8"],
            final_answer="4 se guna karenge, to m = 8",
        ),
    ),
    (
        "4.1",
        _q(
            MCQ,
            RECALL,
            "medium",
            text="2n + 1 = 11 ka solution kya hai?",
            options=["n = 5", "n = 6", "n = 10", "n = 12"],
            correct_option=0,
            hints=["Pehle dono taraf se 1 ghatao.", "Phir dono taraf 2 se bhaag do."],
            concept="Pehle jode gaye number ko hatao, phir guna wale number se bhaag do.",
            steps=["Dono taraf se 1 ghatao: 2n = 10", "Dono taraf 2 se bhaag do: n = 5"],
            final_answer="n = 5",
        ),
    ),
    (
        None,
        _q(
            MCQ,
            CONCEPT,
            "medium",
            text="'Ek number mein 7 jodne par 15 milta hai' ka equation kya hoga?",
            options=["n - 15 = 7", "7n = 15", "n + 7 = 15", "15n = 7"],
            correct_option=2,
            hints=["Number ko n maano. Usme 7 jodne ka matlab hai n + 7."],
            concept="Shabdon ki baat ko equation mein likhne ke liye anjaan number ko variable maante hain.",
            steps=["Number = n", "7 jodne par: n + 7", "Yeh 15 ke barabar hai: n + 7 = 15"],
            final_answer="n + 7 = 15",
        ),
    ),
    (
        None,
        _q(
            MCQ,
            CONCEPT,
            "easy",
            text="Equation solve karne ke baad answer kaise check karte hain?",
            options=[
                "Answer ko equation mein wapas daal kar",
                "Answer ko 2 se guna karke",
                "Sirf left side dekh kar",
                "Check karne ki zarurat nahi hoti",
            ],
            correct_option=0,
            hints=["Agar answer sahi hai to dono sides ka kya hoga?"],
            concept="Sahi solution dalne par equation ki dono sides barabar ho jaati hain.",
            steps=["Answer ko variable ki jagah likho", "Dekho ki left side right side ke barabar hai"],
            final_answer="Answer ko equation mein wapas daal kar",
        ),
    ),
    (
        None,
        _q(
            AR,
            CONCEPT,
            "hard",
            text=(
                "Assertion (A): 2x + 4 = 10 ka solution x = 3 hai.\n"
                "Reason (R): Dono taraf se 4 ghatane aur phir 2 se bhaag dene par x = 3 aata hai."
            ),
            options=[
                "A aur R dono sahi hain, aur R, A ko sahi samjhata hai",
                "A aur R dono sahi hain, par R, A ko nahi samjhata",
                "A sahi hai, par R galat hai",
                "A galat hai, par R sahi hai",
            ],
            correct_option=0,
            hints=["Pehle 2x + 4 = 10 khud solve karo.", "Kya R wahi steps batata hai jo tumne kiye?"],
            concept="Assertion-reason mein dekhte hain ki dono sahi hain ya nahi, aur kya R, A ki wajah hai.",
            steps=["4 ghatao: 2x = 6", "2 se bhaag do: x = 3, to A sahi hai", "R yahi steps batata hai"],
            final_answer="A aur R dono sahi hain, aur R, A ko sahi samjhata hai",
        ),
    ),
    (
        "4.2",
        _q(
            MCQ,
            APPLY,
            "medium",
            text="Ek number aur 9 ka sum 25 hai. Number kya hai?",
            options=["16", "34", "25", "9"],
            correct_option=0,
            hints=["Equation likho: n + 9 = 25."],
            concept="Rozana ki baat ko equation mein likh kar solve karte hain.",
            steps=["n + 9 = 25", "Dono taraf se 9 ghatao: n = 16"],
            final_answer="16",
        ),
    ),
    (
        "4.2",
        _q(
            CASE,
            APPLY,
            "medium",
            case=(
                "Riya ke paas kuch pencils hain. Uski friend 6 pencils aur deti hai. "
                "Ab uske paas 20 pencils hain."
            ),
            text="Kaun sa equation is situation ko dikhata hai?",
            options=["6p = 20", "p + 6 = 20", "p - 20 = 6", "20p = 6"],
            correct_option=1,
            hints=["Shuru ki pencils ko p maano. 6 milne par kya hota hai?"],
            concept="Jo cheez badhti hai uske liye jod (+) likhte hain.",
            steps=["Shuru mein p pencils", "6 aur milne par p + 6", "Ab 20 hain: p + 6 = 20"],
            final_answer="p + 6 = 20",
        ),
    ),
    (
        "4.2",
        _q(
            MCQ,
            HOTS,
            "hard",
            text="Aman apni behen se 3 saal bada hai. Dono ki umar ka sum 21 hai. Aman ki umar kitni hai?",
            options=["9", "10", "12", "18"],
            correct_option=2,
            hints=["Behen ki umar x maano. Aman ki umar x + 3 hogi.", "x + (x + 3) = 21 solve karo."],
            concept="Do anjaan umar ek hi variable se likh kar equation banate hain.",
            steps=["Behen = x, Aman = x + 3", "x + x + 3 = 21, to 2x = 18", "x = 9, to Aman = 12"],
            final_answer="12 saal",
        ),
    ),
    (
        "4.2",
        _q(
            CASE,
            HOTS,
            "hard",
            case="Ek rectangle ki length uski width se 4 cm zyada hai. Uska perimeter 32 cm hai.",
            text="Rectangle ki width kitni hai?",
            options=["4 cm", "6 cm", "10 cm", "14 cm"],
            correct_option=1,
            hints=["Width w maano, to length w + 4.", "Perimeter = 2 × (length + width)."],
            concept="Perimeter ke formula se equation bana kar width nikalte hain.",
            steps=["2 × (w + w + 4) = 32", "4w + 8 = 32, to 4w = 24", "w = 6"],
            final_answer="6 cm",
        ),
    ),
]

CLASS_7_MATHS += [
    (
        None,
        _q(
            SHORT,
            CONCEPT,
            "easy",
            text="Equation aur expression mein kya fark hai? Ek example do.",
            model_answer=(
                "Equation mein barabar (=) ka nishaan hota hai, jaise x + 2 = 5. "
                "Expression mein nahi hota, jaise x + 2."
            ),
            key_points=[
                "equation mein barabar ka nishaan hota hai",
                "expression mein barabar ka nishaan nahi hota",
            ],
            hints=["Dekho kis mein barabar (=) ka nishaan hai."],
            concept="Equation do cheezon ko barabar batata hai; expression sirf ek cheez hai.",
            steps=["x + 2 = 5 mein = hai, to yeh equation hai", "x + 2 mein = nahi, to yeh expression hai"],
            final_answer="Equation mein = hota hai, expression mein nahi.",
        ),
    ),
    (
        "4.1",
        _q(
            SHORT,
            RECALL,
            "easy",
            text="3x = 12 solve karo aur apna answer check karo.",
            model_answer="Dono taraf 3 se bhaag do: x = 4. Check: 3 × 4 = 12, dono sides barabar hain.",
            key_points=["dono taraf 3 se bhaag", "x = 4", "x = 4 daal kar check"],
            hints=["x ko 3 se guna kiya gaya hai. Ulta kaam kya hoga?"],
            concept="Guna ka ulta bhaag hai, isliye dono taraf usi number se bhaag dete hain.",
            steps=["Dono taraf 3 se bhaag do: x = 4", "Check: 3 × 4 = 12"],
            final_answer="x = 4",
        ),
    ),
    (
        None,
        _q(
            SHORT,
            CONCEPT,
            "medium",
            text="Equation solve karte waqt dono taraf ek hi kaam kyon karte hain?",
            model_answer="Taaki dono sides barabar rahein, jaise taraazu ke dono palde barabar rehte hain.",
            key_points=["dono sides barabar rehti hain", "taraazu jaisa balance"],
            hints=["Taraazu ke baare mein socho."],
            concept="Equation ek balance hai: dono taraf ek jaisa badlaav balance ko bana kar rakhta hai.",
            steps=[
                "Equation ki dono sides barabar hoti hain",
                "Ek hi kaam dono taraf karne se woh barabar rehti hain",
            ],
            final_answer="Taaki dono sides barabar rahein.",
        ),
    ),
    (
        "4.1",
        _q(
            SHORT,
            RECALL,
            "easy",
            text="x - 5 = 3 ka solution kya hai? Ek line mein samjhao.",
            model_answer="Dono taraf 5 jodo, to x = 8.",
            key_points=["dono taraf 5 jodo", "x = 8"],
            hints=["x mein se 5 ghataya gaya hai. Use wapas kaise laoge?"],
            concept="Ghatane ka ulta jodna hai.",
            steps=["Dono taraf 5 jodo: x = 3 + 5", "x = 8"],
            final_answer="x = 8",
        ),
    ),
    (
        "4.2",
        _q(
            LONG,
            APPLY,
            "medium",
            text=(
                "Ek number ke 4 guna mein 7 jodne par 31 milta hai. "
                "Equation banao aur number nikalo. Har step samjhao."
            ),
            model_answer=(
                "Number ko n maano. Equation: 4n + 7 = 31. Dono taraf se 7 ghatao: 4n = 24. "
                "Dono taraf 4 se bhaag do: n = 6. Check: 4 × 6 + 7 = 31."
            ),
            key_points=[
                "4n + 7 = 31 likhna",
                "7 ghata kar 4n = 24",
                "4 se bhaag de kar n = 6",
                "answer check karna",
            ],
            hints=[
                "Number ko n maano. 4 guna aur 7 jodna kaise likhoge?",
                "Pehle 7 hatao, phir 4 se bhaag do.",
            ],
            concept="Shabdon se equation bana kar ulte kaam se variable nikalte hain.",
            steps=[
                "Number = n, to 4n + 7 = 31",
                "Dono taraf se 7 ghatao: 4n = 24",
                "Dono taraf 4 se bhaag do: n = 6",
                "Check: 4 × 6 + 7 = 31",
            ],
            final_answer="Number 6 hai.",
        ),
    ),
    (
        "4.2",
        _q(
            LONG,
            HOTS,
            "hard",
            text=(
                "Ek rectangle ki length uski width ki do guna hai. Uska perimeter 36 cm hai. "
                "Length aur width nikalo."
            ),
            model_answer=(
                "Width w maano, to length 2w. Perimeter = 2 × (2w + w) = 6w. "
                "6w = 36, to w = 6 cm aur length = 12 cm."
            ),
            key_points=["width w aur length 2w", "6w = 36", "width 6 cm", "length 12 cm"],
            hints=["Width w maano. Length kitni hogi?", "Perimeter = 2 × (length + width)."],
            concept="Perimeter ke formula se ek variable ki equation banti hai.",
            steps=[
                "Width = w, length = 2w",
                "2 × (2w + w) = 36, to 6w = 36",
                "w = 6 cm",
                "Length = 2 × 6 = 12 cm",
            ],
            final_answer="Width 6 cm, length 12 cm",
        ),
    ),
    (
        None,
        _q(
            LONG,
            APPLY,
            "medium",
            text=(
                "Rohan ne apne bhai ko 8 sikke diye. Ab uske paas 15 sikke bache hain. "
                "Equation banao, solve karo aur check karo."
            ),
            model_answer=(
                "Sikke s maano. Equation: s - 8 = 15. Dono taraf 8 jodo: s = 23. Check: 23 - 8 = 15."
            ),
            key_points=["s - 8 = 15 likhna", "dono taraf 8 jodna", "s = 23", "answer check karna"],
            hints=["Shuru ke sikke s maano. 8 dene ke baad kitne bache?"],
            concept="Jo cheez kam hoti hai uske liye ghatana (-) likhte hain.",
            steps=[
                "Shuru mein s sikke, 8 dene par s - 8",
                "s - 8 = 15",
                "Dono taraf 8 jodo: s = 23",
                "Check: 23 - 8 = 15",
            ],
            final_answer="Rohan ke paas shuru mein 23 sikke the.",
        ),
    ),
]

# UKG, "पाठ 1 फल और जानवर" (scripts/sample_data/ukg-picture-book-sample.txt).
UKG_PICTURES: list[tuple[str | None, GeneratedQuestion]] = [
    (
        None,
        _q(
            PICTURE,
            RECALL,
            "easy",
            text="सेब कौन सा है?",
            options=["🍎 सेब", "🐱 बिल्ली", "🚗 कार"],
            correct_option=0,
            hints=["सेब एक लाल फल है।"],
            concept="सेब एक लाल फल है।",
            steps=["लाल फल 🍎 सेब है।"],
            final_answer="🍎 सेब",
        ),
    ),
    (
        None,
        _q(
            PICTURE,
            RECALL,
            "easy",
            text="म्याऊँ कौन बोलता है?",
            options=["🐶 कुत्ता", "🐱 बिल्ली", "🐄 गाय"],
            correct_option=1,
            hints=["यह जानवर दूध पीना पसंद करता है।"],
            concept="बिल्ली म्याऊँ बोलती है।",
            steps=["🐱 बिल्ली म्याऊँ बोलती है।"],
            final_answer="🐱 बिल्ली",
        ),
    ),
    (
        None,
        _q(
            PICTURE,
            RECALL,
            "easy",
            text="पीला फल कौन सा है?",
            options=["🍌 केला", "🍎 सेब", "🍇 अंगूर"],
            correct_option=0,
            hints=["बंदर को यह फल बहुत पसंद है।"],
            concept="केला पीला होता है।",
            steps=["🍌 केला पीला होता है।"],
            final_answer="🍌 केला",
        ),
    ),
    (
        None,
        _q(
            PICTURE,
            RECALL,
            "easy",
            text="कुत्ता कौन सा है?",
            options=["🐄 गाय", "🐶 कुत्ता", "🍌 केला"],
            correct_option=1,
            hints=["कुत्ता भौं-भौं करता है।"],
            concept="कुत्ता भौं-भौं करता है।",
            steps=["🐶 यह कुत्ता है।"],
            final_answer="🐶 कुत्ता",
        ),
    ),
    (
        None,
        _q(
            PICTURE,
            RECALL,
            "medium",
            text="लाल फल कौन सा है?",
            options=["🍇 अंगूर", "🍌 केला", "🍎 सेब"],
            correct_option=2,
            hints=["इसका रंग लाल है।"],
            concept="सेब लाल होता है।",
            steps=["🍎 सेब लाल होता है।"],
            final_answer="🍎 सेब",
        ),
    ),
    (
        "1.1",
        _q(
            COUNT,
            RECALL,
            "easy",
            text="कितने सेब हैं? 🍎🍎🍎",
            numeric_answer=3,
            hints=["उँगली रख कर एक-एक सेब गिनो।"],
            concept="चीज़ों को एक-एक करके गिनते हैं।",
            steps=["1, 2, 3: तीन सेब।"],
            final_answer="3",
        ),
    ),
    (
        None,
        _q(
            COUNT,
            RECALL,
            "easy",
            text="कितनी बिल्लियाँ हैं? 🐱🐱",
            numeric_answer=2,
            hints=["एक-एक बिल्ली गिनो।"],
            concept="चीज़ों को एक-एक करके गिनते हैं।",
            steps=["1, 2: दो बिल्लियाँ।"],
            final_answer="2",
        ),
    ),
    (
        None,
        _q(
            COUNT,
            RECALL,
            "medium",
            text="कितने केले हैं? 🍌🍌🍌🍌",
            numeric_answer=4,
            hints=["धीरे-धीरे एक-एक केला गिनो।"],
            concept="चीज़ों को एक-एक करके गिनते हैं।",
            steps=["1, 2, 3, 4: चार केले।"],
            final_answer="4",
        ),
    ),
    (
        None,
        _q(
            MATCH,
            RECALL,
            "medium",
            text="जानवर को उसकी आवाज़ से मिलाओ।",
            match_left=["🐶 कुत्ता", "🐱 बिल्ली", "🐄 गाय"],
            match_right=["भौं-भौं", "म्याऊँ", "माँ-माँ"],
            hints=["कुत्ता भौं-भौं करता है।"],
            concept="हर जानवर की अपनी आवाज़ होती है।",
            steps=["🐶 भौं-भौं, 🐱 म्याऊँ, 🐄 माँ-माँ।"],
            final_answer="🐶 भौं-भौं, 🐱 म्याऊँ, 🐄 माँ-माँ",
        ),
    ),
    (
        None,
        _q(
            MCQ,
            RECALL,
            "easy",
            text="गाय हमें क्या देती है?",
            options=["🥛 दूध", "🍎 सेब", "🚗 कार"],
            correct_option=0,
            hints=["सुबह हम इसे गिलास में पीते हैं।"],
            concept="गाय हमें दूध देती है।",
            steps=["🐄 गाय हमें 🥛 दूध देती है।"],
            final_answer="🥛 दूध",
        ),
    ),
]
